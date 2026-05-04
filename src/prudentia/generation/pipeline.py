from __future__ import annotations

from pathlib import Path
from typing import Iterable

from pydantic import BaseModel, Field

from prudentia.codex.adapter import CodexAdapter, CodexTaskRequest, CodexTaskResult, select_codex_adapter
from prudentia.codex.manifests import create_context_manifest, manifest_relative_path
from prudentia.codex.prompts import build_prompt
from prudentia.core.models import ArtifactStatus, TaskKind
from prudentia.core.progress import ProgressEvent, new_run_id
from prudentia.reporting.reports import refresh_reports
from prudentia.simulation.service import SimulationMatrix, simulate_profiles
from prudentia.validation.service import ValidationReport, validate_workspace
from prudentia.workspace.manager import checkpoint_workspace, load_workspace, record_progress, update_status

GENERATION_SEQUENCE = [TaskKind.BRIEF, TaskKind.STARTER, TaskKind.SOLUTION, TaskKind.TESTS, TaskKind.RUBRIC]

EXPECTED_ARTIFACTS: dict[TaskKind, list[str]] = {
    TaskKind.BRIEF: ["brief.md", "README.student.md", "pyproject.toml"],
    TaskKind.STARTER: ["starter/src/assignment.py"],
    TaskKind.SOLUTION: ["solution/src/assignment.py"],
    TaskKind.TESTS: ["tests/visible/test_basic.py", "tests/hidden/test_edge_cases.py"],
    TaskKind.REPAIR: ["solution/src/assignment.py", "tests/visible/test_basic.py", "tests/hidden/test_edge_cases.py"],
    TaskKind.RUBRIC: ["rubric.md"],
    TaskKind.SIMULATIONS: [
        "simulations/weak/src/assignment.py",
        "simulations/partial/src/assignment.py",
        "simulations/misconception/src/assignment.py",
    ],
    TaskKind.REPORT: ["reports/teacher_report.md", "reports/simulation_matrix.md"],
}

STATUS_FOR_TASK: dict[TaskKind, str] = {
    TaskKind.BRIEF: "brief",
    TaskKind.STARTER: "starter",
    TaskKind.SOLUTION: "solution",
    TaskKind.TESTS: "tests",
    TaskKind.RUBRIC: "rubric",
}

REPAIR_INVALIDATES = {
    "solution": ArtifactStatus.DRAFT,
    "tests": ArtifactStatus.DRAFT,
    "validation": ArtifactStatus.NOT_RUN,
    "export": ArtifactStatus.NOT_READY,
}

CODEX_BOOKKEEPING_FILES = {".prudentia/codex_status.json"}
NON_REPAIRABLE_VALIDATION_MARKERS = (
    "Docker is unavailable",
    "Docker image ",
    "Native pytest execution requires",
)


class GenerationRunResult(BaseModel):
    run_id: str
    workspace_id: str
    task_results: list[CodexTaskResult] = Field(default_factory=list)
    checkpoint: str | None = None
    validation_run_id: str | None = None
    validation_ok: bool | None = None
    simulation_run_id: str | None = None
    report_path: str | None = None
    repair_attempts: int = 0
    unresolved_issues: list[str] = Field(default_factory=list)

    @property
    def ok(self) -> bool:
        task_ok = all(result.status == "succeeded" for result in self.task_results)
        validation_ok = self.validation_ok is not False
        return task_ok and validation_ok and not self.unresolved_issues


def normalize_steps(steps: Iterable[str | TaskKind] | None, all_steps: bool = False) -> list[TaskKind]:
    if all_steps:
        return list(GENERATION_SEQUENCE)
    if not steps:
        return []
    normalized: list[TaskKind] = []
    for step in steps:
        normalized.append(step if isinstance(step, TaskKind) else TaskKind(step))
    return normalized


def _codex_changed_workspace(result: CodexTaskResult) -> bool:
    return any(path not in CODEX_BOOKKEEPING_FILES for path in result.changed_files)


def _invalidate_task_outputs(workspace_root: Path, step: TaskKind) -> None:
    if step in STATUS_FOR_TASK:
        update_status(
            workspace_root,
            **{
                STATUS_FOR_TASK[step]: ArtifactStatus.DRAFT,
                "validation": ArtifactStatus.NOT_RUN,
                "export": ArtifactStatus.NOT_READY,
            },
        )
    elif step == TaskKind.REPAIR:
        update_status(workspace_root, **REPAIR_INVALIDATES)
    else:
        update_status(workspace_root, validation=ArtifactStatus.NOT_RUN, export=ArtifactStatus.NOT_READY)


def _invalidate_after_codex_result(workspace_root: Path, step: TaskKind, result: CodexTaskResult) -> None:
    if result.status == "succeeded" or _codex_changed_workspace(result):
        _invalidate_task_outputs(workspace_root, step)


def _should_attempt_repair(report: ValidationReport | None) -> bool:
    if report is None:
        return False
    issues = list(getattr(report, "unresolved_issues", []) or [])
    if any(any(marker in issue for marker in NON_REPAIRABLE_VALIDATION_MARKERS) for issue in issues):
        return False
    return True


def _run_codex_task(workspace_root: Path, step: TaskKind, adapter: CodexAdapter, run_id: str) -> CodexTaskResult:
    workspace = load_workspace(workspace_root)
    manifest = create_context_manifest(workspace, step)
    manifest_path = manifest_relative_path(workspace, manifest)
    prompt = build_prompt(step, workspace.metadata, manifest_path)
    request = CodexTaskRequest(
        task_kind=step,
        prompt=prompt,
        context_manifest_path=manifest_path,
        allowed_write_globs=manifest.allowed_write_globs,
        expected_artifacts=EXPECTED_ARTIFACTS.get(step, []),
        mode="workspace_write",
    )
    record_progress(
        workspace.root,
        ProgressEvent(
            run_id=run_id,
            workspace_id=workspace.id,
            event_kind="codex_task_start",
            message=f"{step.value} generation started.",
            payload={"manifest_id": manifest.manifest_id},
        ).model_dump(mode="json"),
    )
    result = adapter.run_task(workspace, request)
    _invalidate_after_codex_result(workspace.root, step, result)
    if result.status != "succeeded":
        record_progress(
            workspace.root,
            ProgressEvent(
                run_id=run_id,
                workspace_id=workspace.id,
                event_kind="error",
                message=f"{step.value} generation failed: {result.summary}",
                payload=result.model_dump(mode="json"),
            ).model_dump(mode="json"),
        )
        return result
    record_progress(
        workspace.root,
        ProgressEvent(
            run_id=run_id,
            workspace_id=workspace.id,
            event_kind="codex_task_finish",
            message=f"{step.value} generation finished.",
            payload=result.model_dump(mode="json"),
        ).model_dump(mode="json"),
    )
    return result


def generate_steps(
    root: Path | str, steps: list[TaskKind], *, use_live_codex: bool = False, checkpoint: bool = False
) -> GenerationRunResult:
    workspace = load_workspace(root)
    run_id = new_run_id("generate")
    record_progress(
        workspace.root,
        ProgressEvent(
            run_id=run_id,
            workspace_id=workspace.id,
            event_kind="run_start",
            message="Generation run started.",
            payload={"steps": [step.value for step in steps], "live_codex": use_live_codex},
        ).model_dump(mode="json"),
    )
    checkpoint_path: str | None = None
    if checkpoint:
        checkpoint_path = checkpoint_workspace(workspace.root, "before-generate-all").relative_to(workspace.root).as_posix()

    adapter = select_codex_adapter(use_live_codex)
    task_results: list[CodexTaskResult] = []
    for step in steps:
        result = _run_codex_task(workspace.root, step, adapter, run_id)
        task_results.append(result)
        if result.status != "succeeded":
            break
    return GenerationRunResult(run_id=run_id, workspace_id=workspace.id, task_results=task_results, checkpoint=checkpoint_path)


def _validation_issue_summary(report: ValidationReport | None, exc: Exception | None = None) -> list[str]:
    if exc:
        return [str(exc)]
    if not report:
        return ["Validation did not produce a report."]
    return list(report.unresolved_issues)


def generate_all(
    root: Path | str,
    *,
    use_live_codex: bool = False,
    allow_native_execution: bool = False,
    prefer_docker: bool = True,
    max_repair_attempts: int = 2,
) -> GenerationRunResult:
    result = generate_steps(root, list(GENERATION_SEQUENCE), use_live_codex=use_live_codex, checkpoint=True)
    workspace = load_workspace(root)
    unresolved: list[str] = []
    validation: ValidationReport | None = None
    validation_exc: Exception | None = None
    simulation: SimulationMatrix | None = None
    report_path: str | None = None

    if result.ok:
        try:
            validation = validate_workspace(workspace.root, allow_native_execution=allow_native_execution, prefer_docker=prefer_docker)
        except Exception as exc:
            validation_exc = exc
        adapter = select_codex_adapter(use_live_codex)
        while (
            validation is not None
            and not validation.ok
            and _should_attempt_repair(validation)
            and validation_exc is None
            and result.repair_attempts < max(0, max_repair_attempts)
        ):
            attempt = result.repair_attempts + 1
            record_progress(
                workspace.root,
                ProgressEvent(
                    run_id=result.run_id,
                    workspace_id=workspace.id,
                    event_kind="repair_start",
                    message=f"Repair attempt {attempt} started.",
                    payload={"attempt": attempt, "max_attempts": max_repair_attempts},
                ).model_dump(mode="json"),
            )
            repair_result = _run_codex_task(workspace.root, TaskKind.REPAIR, adapter, result.run_id)
            result.task_results.append(repair_result)
            result.repair_attempts = attempt
            if repair_result.status != "succeeded":
                break
            try:
                validation = validate_workspace(workspace.root, allow_native_execution=allow_native_execution, prefer_docker=prefer_docker)
            except Exception as exc:
                validation_exc = exc
                break
        if validation and validation.ok:
            simulation = simulate_profiles(
                workspace.root,
                allow_native_execution=allow_native_execution,
                prefer_docker=prefer_docker,
            )
        unresolved = _validation_issue_summary(validation, validation_exc) if not validation or not validation.ok else []
    else:
        unresolved = [issue for task in result.task_results for issue in task.unresolved_issues]

    try:
        report_path = refresh_reports(workspace.root).relative_to(workspace.root).as_posix()
    except Exception as exc:
        unresolved.append(f"Report refresh failed: {exc}")

    result.validation_run_id = validation.run_id if validation else None
    result.validation_ok = validation.ok if validation else False
    result.simulation_run_id = simulation.run_id if simulation else None
    result.report_path = report_path
    result.unresolved_issues = unresolved
    return result
