from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel

from prudentia.core.jsonio import read_json, write_json
from prudentia.core.models import ArtifactStatus
from prudentia.core.progress import ProgressEvent, new_run_id
from prudentia.core.time import utc_now_iso
from prudentia.runner.test_runner import PytestRunResult, run_pytest
from prudentia.validation.artifacts import ArtifactValidationResult, validate_artifacts
from prudentia.workspace.manager import load_workspace, record_progress, update_status


class ValidationReport(BaseModel):
    schema_version: str = "0.1"
    workspace_id: str
    run_id: str
    created_at: str
    artifact_validation: ArtifactValidationResult
    pytest_result: PytestRunResult | None = None
    pytest_summary: dict[str, Any] | None = None
    ok: bool
    unresolved_issues: list[str]


def load_pytest_summary(report_path: str | None) -> dict[str, Any] | None:
    if not report_path:
        return None
    path = Path(report_path)
    if not path.exists():
        return None
    try:
        data = read_json(path)
    except Exception:
        return None
    return data.get("summary", data)


def validate_workspace(
    root: Path | str,
    *,
    allow_native_execution: bool = False,
    prefer_docker: bool = True,
) -> ValidationReport:
    workspace = load_workspace(root)
    run_id = new_run_id("validate")
    record_progress(
        workspace.root,
        ProgressEvent(
            run_id=run_id,
            workspace_id=workspace.id,
            event_kind="validation_start",
            message="Validation started.",
            payload={"prefer_docker": prefer_docker, "allow_native_execution": allow_native_execution},
        ).model_dump(mode="json"),
    )
    artifact_result = validate_artifacts(workspace.root)
    pytest_result: PytestRunResult | None = None
    unresolved = [issue.message for issue in artifact_result.issues]
    if artifact_result.ok:
        try:
            pytest_result = run_pytest(
                workspace.root,
                target="solution",
                allow_native_execution=allow_native_execution,
                prefer_docker=prefer_docker,
            )
            if not pytest_result.ok:
                unresolved.append("Reference solution did not pass visible and instructor checks.")
        except Exception as exc:
            unresolved.append(str(exc))
    ok = artifact_result.ok and pytest_result is not None and pytest_result.ok
    report = ValidationReport(
        workspace_id=workspace.id,
        run_id=run_id,
        created_at=utc_now_iso(),
        artifact_validation=artifact_result,
        pytest_result=pytest_result,
        pytest_summary=load_pytest_summary(pytest_result.pytest_report_path if pytest_result else None),
        ok=ok,
        unresolved_issues=unresolved,
    )
    write_json(workspace.path("reports/validation_report.json"), report)
    update_status(workspace.root, validation=ArtifactStatus.PASSED if ok else ArtifactStatus.FAILED)
    record_progress(
        workspace.root,
        ProgressEvent(
            run_id=run_id,
            workspace_id=workspace.id,
            event_kind="validation_finish" if ok else "error",
            message="Validation passed." if ok else "Validation failed.",
            payload=report.model_dump(mode="json"),
        ).model_dump(mode="json"),
    )
    return report
