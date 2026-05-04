from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from prudentia.core.doctor import run_doctor
from prudentia.core.models import ArtifactStatus, TaskKind
from prudentia.export.packager import ExportReadinessError, package_export
from prudentia.export.scanner import ExportSafetyError
from prudentia.generation.pipeline import generate_all, generate_steps
from prudentia.reporting.reports import refresh_reports
from prudentia.simulation.service import simulate_profiles
from prudentia.validation.service import validate_workspace
from prudentia.workspace.manager import clean_runs as clean_workspace_runs
from prudentia.workspace.manager import create_workspace, find_workspace_root, load_workspace, update_status

app = typer.Typer(no_args_is_help=True, help="Prudentia local-first assignment workbench MVP.")
APPROVABLE_ARTIFACTS = {"brief", "starter", "solution", "tests", "rubric"}


def _workspace_root(workspace: Optional[Path]) -> Path:
    return find_workspace_root(workspace or Path.cwd())


def _print_json(payload: object) -> None:
    if hasattr(payload, "model_dump"):
        typer.echo(json.dumps(payload.model_dump(mode="json"), indent=2, sort_keys=True))
    else:
        typer.echo(json.dumps(payload, indent=2, sort_keys=True))


@app.command()
def doctor(json_output: bool = typer.Option(False, "--json", help="Print machine-readable doctor report.")) -> None:
    """Check local runtime, Codex, Docker, and pytest readiness."""
    report = run_doctor()
    if json_output:
        _print_json(report)
        return
    for check in report.checks:
        marker = "OK" if check.ok else "WARN"
        typer.echo(f"[{marker}] {check.name}: {check.detail}")


@app.command()
def ui(
    port: int = typer.Option(4898, "--port", min=1024, max=65535, help="Local UI port."),
    workspace: Optional[Path] = typer.Option(None, "--workspace", help="Optional workspace path to preselect."),
) -> None:
    """Launch the local browser workbench and API server."""
    import os

    import uvicorn

    if workspace:
        os.environ["PRUDENTIA_WORKSPACE"] = str(workspace.expanduser().resolve())
    typer.echo(f"Prudentia UI: http://127.0.0.1:{port}")
    uvicorn.run("prudentia.server.app:create_app", factory=True, host="127.0.0.1", port=port, log_level="info")


@app.command()
def create(
    title: str = typer.Option(..., "--title", help="Assignment title."),
    course: str = typer.Option(..., "--course", help="Course name, for example CS101."),
    topic: str = typer.Option(..., "--topic", help="Assignment topic."),
    difficulty: str = typer.Option(..., "--difficulty", help="Difficulty label."),
    root: Optional[Path] = typer.Option(None, "--root", help="Directory in which the workspace folder is created."),
    estimated_minutes: int = typer.Option(45, "--estimated-minutes", min=5, max=600),
    learning_objectives: Optional[str] = typer.Option(None, "--learning-objectives", help="Semicolon-separated objectives."),
    constraints: Optional[str] = typer.Option(None, "--constraints", help="Semicolon-separated constraints."),
    slug: Optional[str] = typer.Option(None, "--slug", help="Override generated slug."),
) -> None:
    """Create a deterministic local assignment workspace."""
    objectives = [item.strip() for item in learning_objectives.split(";")] if learning_objectives else None
    parsed_constraints = [item.strip() for item in constraints.split(";")] if constraints else None
    workspace = create_workspace(
        root or Path.cwd(),
        title=title,
        course=course,
        topic=topic,
        difficulty=difficulty,
        estimated_minutes=estimated_minutes,
        learning_objectives=objectives,
        constraints=parsed_constraints,
        slug=slug,
    )
    typer.echo(str(workspace.root))


@app.command()
def generate(
    all_steps: bool = typer.Option(False, "--all", help="Generate brief, starter, solution, tests, and rubric."),
    brief: bool = typer.Option(False, "--brief", help="Generate brief and student README."),
    starter: bool = typer.Option(False, "--starter", help="Generate starter code."),
    solution: bool = typer.Option(False, "--solution", help="Generate reference solution."),
    tests: bool = typer.Option(False, "--tests", help="Generate visible and instructor tests."),
    rubric: bool = typer.Option(False, "--rubric", help="Generate rubric."),
    simulations: bool = typer.Option(False, "--simulations", help="Generate simulated submissions."),
    report: bool = typer.Option(False, "--report", help="Refresh report artifacts."),
    workspace: Optional[Path] = typer.Option(None, "--workspace", help="Workspace path; defaults to current workspace."),
    use_codex: bool = typer.Option(False, "--use-codex", help="Attempt live Codex instead of deterministic local generation."),
    allow_native_execution: bool = typer.Option(
        False, "--allow-native-execution", help="With --all, explicitly run validation and simulation on the host through ephemeral copies."
    ),
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable result."),
) -> None:
    """Run Generate All or an individual generation step."""
    root = _workspace_root(workspace)
    if all_steps:
        result = generate_all(
            root, use_live_codex=use_codex, allow_native_execution=allow_native_execution, prefer_docker=not allow_native_execution
        )
    else:
        steps: list[TaskKind] = []
        if brief:
            steps.append(TaskKind.BRIEF)
        if starter:
            steps.append(TaskKind.STARTER)
        if solution:
            steps.append(TaskKind.SOLUTION)
        if tests:
            steps.append(TaskKind.TESTS)
        if rubric:
            steps.append(TaskKind.RUBRIC)
        if simulations:
            steps.append(TaskKind.SIMULATIONS)
        if report:
            steps.append(TaskKind.REPORT)
        if not steps:
            raise typer.BadParameter("Choose --all or at least one generation step.")
        result = generate_steps(root, steps, use_live_codex=use_codex)
    if json_output:
        _print_json(result)
    else:
        typer.echo(f"Generation {'passed' if result.ok else 'failed'}: {result.run_id}")
        for task in result.task_results:
            typer.echo(f"- {task.task_kind.value}: {task.status}; changed {len(task.changed_files)} file(s)")
        if result.validation_ok is not None:
            typer.echo(f"Validation: {'passed' if result.validation_ok else 'failed'}")
        if result.report_path:
            typer.echo(f"Report: {result.report_path}")
    if not result.ok:
        raise typer.Exit(1)


@app.command()
def approve(
    artifact: Optional[str] = typer.Argument(None, help="Artifact to approve: brief, starter, solution, tests, or rubric."),
    all_artifacts: bool = typer.Option(False, "--all", help="Approve all reviewable artifacts."),
    workspace: Optional[Path] = typer.Option(None, "--workspace", help="Workspace path; defaults to current workspace."),
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable status."),
) -> None:
    """Mark reviewed artifacts as approved before export."""
    root = _workspace_root(workspace)
    if all_artifacts:
        selected = sorted(APPROVABLE_ARTIFACTS)
    elif artifact in APPROVABLE_ARTIFACTS:
        selected = [artifact]
    else:
        raise typer.BadParameter("Choose --all or one of: brief, starter, solution, tests, rubric.")
    updates = {item: ArtifactStatus.APPROVED for item in selected}
    updated = update_status(root, **updates)
    if json_output:
        _print_json(updated.metadata.status)
    else:
        typer.echo(f"Approved: {', '.join(selected)}")


@app.command()
def validate(
    workspace: Optional[Path] = typer.Option(None, "--workspace", help="Workspace path; defaults to current workspace."),
    allow_native_execution: bool = typer.Option(
        False, "--allow-native-execution", help="Explicitly run pytest on the host through an ephemeral copy."
    ),
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable report."),
) -> None:
    """Validate required artifacts and run pytest against the reference solution."""
    root = _workspace_root(workspace)
    report = validate_workspace(root, allow_native_execution=allow_native_execution, prefer_docker=not allow_native_execution)
    if json_output:
        _print_json(report)
    else:
        typer.echo(f"Validation {'passed' if report.ok else 'failed'}: {report.run_id}")
        if report.unresolved_issues:
            for issue in report.unresolved_issues:
                typer.echo(f"- {issue}")
    if not report.ok:
        raise typer.Exit(1)


@app.command()
def simulate(
    profiles: str = typer.Option("weak,partial,misconception", "--profiles", help="Comma-separated profiles."),
    workspace: Optional[Path] = typer.Option(None, "--workspace", help="Workspace path; defaults to current workspace."),
    allow_native_execution: bool = typer.Option(
        False, "--allow-native-execution", help="Explicitly run pytest on the host through ephemeral copies."
    ),
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable matrix."),
) -> None:
    """Generate simulated submissions and run tests against them."""
    root = _workspace_root(workspace)
    matrix = simulate_profiles(
        root, profiles=profiles, allow_native_execution=allow_native_execution, prefer_docker=not allow_native_execution
    )
    if json_output:
        _print_json(matrix)
    else:
        typer.echo(f"Simulation matrix written: {matrix.run_id}")
        for row in matrix.rows:
            typer.echo(f"- {row.profile}: passed={row.passed} failed={row.failed} exit={row.exit_code}")


@app.command()
def report(
    workspace: Optional[Path] = typer.Option(None, "--workspace", help="Workspace path; defaults to current workspace."),
) -> None:
    """Refresh reports/teacher_report.md."""
    root = _workspace_root(workspace)
    path = refresh_reports(root)
    typer.echo(str(path))


@app.command(name="export")
def export_command(
    kind: str = typer.Argument(..., help="student or teacher"),
    workspace: Optional[Path] = typer.Option(None, "--workspace", help="Workspace path; defaults to current workspace."),
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable manifest."),
) -> None:
    """Create student or teacher ZIP exports with safety scanning."""
    if kind not in {"student", "teacher"}:
        raise typer.BadParameter("kind must be student or teacher")
    root = _workspace_root(workspace)
    try:
        manifest = package_export(root, kind)  # type: ignore[arg-type]
    except ExportReadinessError as exc:
        typer.echo(str(exc), err=True)
        for reason in exc.manifest.block_reasons:
            typer.echo(f"- {reason}", err=True)
        raise typer.Exit(1) from exc
    except ExportSafetyError as exc:
        typer.echo(str(exc), err=True)
        for finding in exc.scan_result.findings:
            typer.echo(f"- {finding.path}: {finding.reason}", err=True)
        raise typer.Exit(1) from exc
    if json_output:
        _print_json(manifest)
    else:
        typer.echo(manifest.zip_path)


@app.command()
def status(
    workspace: Optional[Path] = typer.Option(None, "--workspace", help="Workspace path; defaults to current workspace."),
    json_output: bool = typer.Option(False, "--json", help="Print machine-readable status."),
) -> None:
    """Print workspace metadata and artifact status."""
    root = _workspace_root(workspace)
    ws = load_workspace(root)
    artifacts = {
        "brief.md": ws.path("brief.md").exists(),
        "starter/src/assignment.py": ws.path("starter/src/assignment.py").exists(),
        "solution/src/assignment.py": ws.path("solution/src/assignment.py").exists(),
        "tests/visible/test_basic.py": ws.path("tests/visible/test_basic.py").exists(),
        "tests/hidden/test_edge_cases.py": ws.path("tests/hidden/test_edge_cases.py").exists(),
        "rubric.md": ws.path("rubric.md").exists(),
        "reports/validation_report.json": ws.path("reports/validation_report.json").exists(),
        "reports/simulation_matrix.md": ws.path("reports/simulation_matrix.md").exists(),
    }
    payload = {
        "workspace": str(ws.root),
        "id": ws.id,
        "title": ws.metadata.title,
        "status": ws.metadata.status.model_dump(mode="json"),
        "artifacts": artifacts,
    }
    if json_output:
        _print_json(payload)
    else:
        typer.echo(f"Workspace: {payload['workspace']}")
        typer.echo(f"Title: {payload['title']}")
        typer.echo(f"Status: {payload['status']}")
        for path, exists in artifacts.items():
            typer.echo(f"- {path}: {'present' if exists else 'missing'}")


@app.command("clean-runs")
def clean_runs(
    workspace: Optional[Path] = typer.Option(None, "--workspace", help="Workspace path; defaults to current workspace."),
) -> None:
    """Delete local run records from .prudentia/runs."""
    root = _workspace_root(workspace)
    count = clean_workspace_runs(root)
    typer.echo(f"Removed {count} run record(s).")
