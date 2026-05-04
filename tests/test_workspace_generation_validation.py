from __future__ import annotations

import subprocess
import zipfile
from pathlib import Path

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from prudentia.codex.adapter import CodexTaskRequest, CodexTaskResult, LiveCodexAdapter, OfflineCodexAdapter
from prudentia.core.doctor import run_doctor
from prudentia.core.models import ArtifactStatus, CourseProfile, TaskKind, WorkspaceMetadata
from prudentia.export.packager import ExportReadinessError, package_export
from prudentia.export.scanner import ExportSafetyError
from prudentia.generation.pipeline import GENERATION_SEQUENCE, generate_all, generate_steps
from prudentia.reporting.reports import refresh_reports
from prudentia.simulation.service import simulate_profiles
from prudentia.validation.artifacts import validate_artifacts
from prudentia.validation.service import validate_workspace
from prudentia.workspace.manager import create_workspace, find_workspace_root, load_workspace, update_status


def make_workspace(tmp_path: Path) -> Path:
    workspace = create_workspace(
        tmp_path,
        title="Palindrome checker",
        course="CS101",
        topic="strings and functions",
        difficulty="beginner",
    )
    return workspace.root


def generate_assignment(root: Path) -> None:
    result = generate_steps(root, list(GENERATION_SEQUENCE))
    assert result.ok, result.model_dump(mode="json")


def approve_all(root: Path) -> None:
    update_status(
        root,
        brief=ArtifactStatus.APPROVED,
        starter=ArtifactStatus.APPROVED,
        solution=ArtifactStatus.APPROVED,
        tests=ArtifactStatus.APPROVED,
        rubric=ArtifactStatus.APPROVED,
    )


def test_workspace_creation_writes_required_structure(tmp_path: Path) -> None:
    root = make_workspace(tmp_path)
    required = [
        "prudentia.yaml",
        ".codex/config.toml",
        ".prudentia/workflow_state.json",
        ".prudentia/action_log.jsonl",
        ".prudentia/context_manifests",
        ".prudentia/runs",
        ".prudentia/checkpoints",
        ".prudentia/export_manifests",
        "starter",
        "solution",
        "tests/visible",
        "tests/hidden",
        "simulations",
        "reports",
        "exports",
    ]
    for relative in required:
        assert (root / relative).exists(), relative
    workspace = load_workspace(root)
    assert workspace.metadata.title == "Palindrome checker"
    assert workspace.metadata.language.version == "3.12"


def test_schemas_reject_invalid_workspace_metadata() -> None:
    with pytest.raises(ValidationError):
        WorkspaceMetadata(
            title="Bad",
            slug="../bad",
            course=CourseProfile(name="CS101"),
            assignment={"topic": "strings", "difficulty": "beginner"},
        )


def test_generation_creates_required_assignment_artifacts(tmp_path: Path) -> None:
    root = make_workspace(tmp_path)
    result = generate_all(root, allow_native_execution=True, prefer_docker=False)
    assert result.ok, result.model_dump(mode="json")
    assert result.validation_ok is True
    assert result.validation_run_id
    assert result.simulation_run_id
    assert result.report_path == "reports/teacher_report.md"
    for relative in [
        "brief.md",
        "README.student.md",
        "pyproject.toml",
        "starter/src/assignment.py",
        "solution/src/assignment.py",
        "tests/visible/test_basic.py",
        "tests/hidden/test_edge_cases.py",
        "rubric.md",
        "reports/validation_report.json",
        "reports/simulation_matrix.md",
        "reports/teacher_report.md",
    ]:
        assert (root / relative).exists(), relative


def test_starter_does_not_contain_complete_solution_marker(tmp_path: Path) -> None:
    root = make_workspace(tmp_path)
    generate_assignment(root)
    starter = (root / "starter/src/assignment.py").read_text(encoding="utf-8")
    assert "return normalized == normalized[::-1]" not in starter
    assert "REFERENCE SOLUTION" not in starter
    assert "NotImplementedError" in starter


def test_validator_detects_missing_required_file(tmp_path: Path) -> None:
    root = make_workspace(tmp_path)
    generate_assignment(root)
    (root / "brief.md").unlink()
    result = validate_artifacts(root)
    assert not result.ok
    assert any(issue.code == "missing_required_file" and issue.path == "brief.md" for issue in result.issues)


def test_reference_solution_passes_generated_pytest_tests_native(tmp_path: Path) -> None:
    root = make_workspace(tmp_path)
    generate_assignment(root)
    report = validate_workspace(root, allow_native_execution=True, prefer_docker=False)
    assert report.ok, report.model_dump(mode="json")
    assert report.pytest_result is not None
    assert Path(report.pytest_result.pytest_report_path).exists()
    assert (root / "reports/validation_report.json").exists()


def test_simulation_matrix_is_written(tmp_path: Path) -> None:
    root = make_workspace(tmp_path)
    generate_assignment(root)
    matrix = simulate_profiles(root, profiles="weak,partial,misconception", allow_native_execution=True, prefer_docker=False)
    assert {row.profile for row in matrix.rows} == {"weak", "partial", "misconception"}
    assert (root / "reports/simulation_matrix.md").exists()


def test_student_export_excludes_teacher_only_paths(tmp_path: Path) -> None:
    root = make_workspace(tmp_path)
    generate_assignment(root)
    validate_workspace(root, allow_native_execution=True, prefer_docker=False)
    simulate_profiles(root, allow_native_execution=True, prefer_docker=False)
    refresh_reports(root)
    approve_all(root)
    manifest = package_export(root, "student")
    assert manifest.zip_path is not None
    with zipfile.ZipFile(root / manifest.zip_path) as archive:
        names = set(archive.namelist())
    forbidden_prefixes = ["solution/", "tests/hidden/", "reports/", ".prudentia/", ".codex/", "simulations/", "exports/"]
    for name in names:
        assert not any(name.startswith(prefix) for prefix in forbidden_prefixes), name
    assert "brief.md" in names
    assert "starter/src/assignment.py" in names
    assert "tests/visible/test_basic.py" in names


def test_export_blocks_until_approval_and_validation_pass(tmp_path: Path) -> None:
    root = make_workspace(tmp_path)
    generate_assignment(root)
    validate_workspace(root, allow_native_execution=True, prefer_docker=False)
    with pytest.raises(ExportReadinessError) as exc_info:
        package_export(root, "student")
    manifest = exc_info.value.manifest
    assert manifest.status == "blocked"
    assert manifest.zip_path is None
    assert any("brief must be approved" in reason for reason in manifest.block_reasons)
    assert list((root / ".prudentia/export_manifests").glob("*.json"))
    assert not (root / "exports/student/palindrome-checker-student.zip").exists()


def test_regeneration_resets_validation_before_export(tmp_path: Path) -> None:
    root = make_workspace(tmp_path)
    generate_assignment(root)
    validate_workspace(root, allow_native_execution=True, prefer_docker=False)
    approve_all(root)
    assert package_export(root, "student").zip_path is not None

    result = generate_steps(root, [TaskKind.TESTS])
    assert result.ok
    update_status(root, tests=ArtifactStatus.APPROVED)

    with pytest.raises(ExportReadinessError) as exc_info:
        package_export(root, "student")
    assert "validation must pass before export." in exc_info.value.manifest.block_reasons


def test_failed_mutating_generation_resets_validation_before_export(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = make_workspace(tmp_path)
    generate_assignment(root)
    validate_workspace(root, allow_native_execution=True, prefer_docker=False)
    approve_all(root)
    assert package_export(root, "student").zip_path is not None

    class FailedMutatingAdapter:
        def readiness(self) -> object:
            return object()

        def run_task(self, workspace: object, request: CodexTaskRequest) -> CodexTaskResult:
            root_path = getattr(workspace, "root")
            (root_path / "tests/visible/test_basic.py").write_text("def test_broken():\n    assert False\n", encoding="utf-8")
            return CodexTaskResult(
                task_kind=request.task_kind,
                status="failed",
                started_at="start",
                finished_at="finish",
                changed_files=["tests/visible/test_basic.py"],
                unresolved_issues=["forced failure"],
                summary="failed after mutating tests",
            )

    monkeypatch.setattr("prudentia.generation.pipeline.select_codex_adapter", lambda use_live_codex=False: FailedMutatingAdapter())
    result = generate_steps(root, [TaskKind.TESTS])
    assert not result.ok
    update_status(root, tests=ArtifactStatus.APPROVED)

    with pytest.raises(ExportReadinessError) as exc_info:
        package_export(root, "student")
    assert "validation must pass before export." in exc_info.value.manifest.block_reasons


def test_student_export_blocks_forbidden_content_leaks(tmp_path: Path) -> None:
    root = make_workspace(tmp_path)
    generate_assignment(root)
    validate_workspace(root, allow_native_execution=True, prefer_docker=False)
    approve_all(root)
    starter = root / "starter/src/assignment.py"
    starter.write_text(starter.read_text(encoding="utf-8") + "\n# REFERENCE SOLUTION\n", encoding="utf-8")
    with pytest.raises(ExportSafetyError):
        package_export(root, "student")


def test_teacher_export_blocks_credential_like_content(tmp_path: Path) -> None:
    root = make_workspace(tmp_path)
    generate_assignment(root)
    validate_workspace(root, allow_native_execution=True, prefer_docker=False)
    approve_all(root)
    (root / "reports/teacher_report.md").write_text("accidental OPENAI_API_KEY=sk-abcdefghi\n", encoding="utf-8")
    with pytest.raises(ExportSafetyError):
        package_export(root, "teacher")


def test_current_workspace_marker_resolves_latest_created_workspace(tmp_path: Path) -> None:
    root = make_workspace(tmp_path)
    assert find_workspace_root(tmp_path) == root


def test_codex_write_boundary_violations_fail_task(tmp_path: Path) -> None:
    root = make_workspace(tmp_path)
    workspace = load_workspace(root)
    result = OfflineCodexAdapter().run_task(
        workspace,
        CodexTaskRequest(
            task_kind=TaskKind.BRIEF,
            prompt="Generate brief only.",
            context_manifest_path=".prudentia/context_manifests/test.json",
            allowed_write_globs=["brief.md"],
            expected_artifacts=["brief.md"],
        ),
    )
    assert result.status == "failed"
    assert any("outside allowed write globs" in issue for issue in result.unresolved_issues)
    assert "README.student.md" in ", ".join(result.unresolved_issues)


def test_live_codex_cli_prompt_bookkeeping_does_not_violate_write_boundary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = make_workspace(tmp_path)
    workspace = load_workspace(root)

    def fake_which(name: str) -> str | None:
        return "/tmp/fake-codex" if name == "codex" else None

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if "--version" in command:
            return subprocess.CompletedProcess(command, 0, stdout="codex fake", stderr="")
        cwd = Path(str(kwargs["cwd"]))
        (cwd / "brief.md").write_text("# Brief\n", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="no changes", stderr="")

    monkeypatch.setattr("shutil.which", fake_which)
    monkeypatch.setattr("subprocess.run", fake_run)
    result = LiveCodexAdapter().run_task(
        workspace,
        CodexTaskRequest(
            task_kind=TaskKind.BRIEF,
            prompt="Generate brief only.",
            context_manifest_path=".prudentia/context_manifests/test.json",
            allowed_write_globs=["brief.md"],
            expected_artifacts=["brief.md"],
        ),
    )
    assert result.status == "succeeded"
    assert result.unresolved_issues == []
    assert result.changed_files == ["brief.md"]


def test_live_codex_cli_missing_expected_artifact_fails_task(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = make_workspace(tmp_path)
    workspace = load_workspace(root)

    def fake_which(name: str) -> str | None:
        return "/tmp/fake-codex" if name == "codex" else None

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if "--version" in command:
            return subprocess.CompletedProcess(command, 0, stdout="codex fake", stderr="")
        return subprocess.CompletedProcess(command, 0, stdout="could not write", stderr="")

    monkeypatch.setattr("shutil.which", fake_which)
    monkeypatch.setattr("subprocess.run", fake_run)
    result = LiveCodexAdapter().run_task(
        workspace,
        CodexTaskRequest(
            task_kind=TaskKind.BRIEF,
            prompt="Generate brief only.",
            context_manifest_path=".prudentia/context_manifests/test.json",
            allowed_write_globs=["brief.md"],
            expected_artifacts=["brief.md"],
        ),
    )
    assert result.status == "failed"
    assert any("did not produce expected artifacts" in issue for issue in result.unresolved_issues)


def test_live_codex_cli_run_tree_writes_violate_write_boundary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = make_workspace(tmp_path)
    workspace = load_workspace(root)

    def fake_which(name: str) -> str | None:
        return "/tmp/fake-codex" if name == "codex" else None

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if "--version" in command:
            return subprocess.CompletedProcess(command, 0, stdout="codex fake", stderr="")
        cwd = Path(str(kwargs["cwd"]))
        (cwd / ".prudentia/runs/injected.txt").write_text("unexpected write\n", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="changed run tree", stderr="")

    monkeypatch.setattr("shutil.which", fake_which)
    monkeypatch.setattr("subprocess.run", fake_run)
    result = LiveCodexAdapter().run_task(
        workspace,
        CodexTaskRequest(
            task_kind=TaskKind.BRIEF,
            prompt="Generate brief only.",
            context_manifest_path=".prudentia/context_manifests/test.json",
            allowed_write_globs=["brief.md"],
            expected_artifacts=["brief.md"],
        ),
    )
    assert result.status == "failed"
    assert any(".prudentia/runs/injected.txt" in issue for issue in result.unresolved_issues)


def test_generate_all_repair_loop_stops_after_two_attempts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = make_workspace(tmp_path)

    def always_fails(*args: object, **kwargs: object) -> object:
        return type("ValidationStub", (), {"ok": False, "run_id": "validate-stub", "unresolved_issues": ["still failing"]})()

    monkeypatch.setattr("prudentia.generation.pipeline.validate_workspace", always_fails)
    result = generate_all(root, allow_native_execution=True, prefer_docker=False)
    assert not result.ok
    assert result.repair_attempts == 2
    assert [task.task_kind for task in result.task_results].count(TaskKind.REPAIR) == 2
    assert result.unresolved_issues == ["still failing"]


def test_doctor_reports_missing_docker_image(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_which(name: str) -> str | None:
        return "/usr/bin/docker" if name == "docker" else None

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if command[:2] == ["/usr/bin/docker", "info"]:
            return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")
        if command[:3] == ["/usr/bin/docker", "image", "inspect"]:
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="missing")
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="unexpected")

    monkeypatch.setattr("shutil.which", fake_which)
    monkeypatch.setattr("subprocess.run", fake_run)
    report = run_doctor()
    image_check = next(check for check in report.checks if check.name == "docker-image")
    assert not image_check.ok
    assert "is missing" in image_check.detail


def test_validation_reports_missing_docker_image_before_running_container(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = make_workspace(tmp_path)
    generate_assignment(root)

    def fake_which(name: str) -> str | None:
        return "/usr/bin/docker" if name == "docker" else None

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if command[:2] == ["/usr/bin/docker", "info"]:
            return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")
        if command[:3] == ["/usr/bin/docker", "image", "inspect"]:
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="missing")
        raise AssertionError(f"unexpected docker command: {command}")

    monkeypatch.setattr("shutil.which", fake_which)
    monkeypatch.setattr("subprocess.run", fake_run)
    report = validate_workspace(root, allow_native_execution=False, prefer_docker=True)
    assert not report.ok
    assert any("Docker image prudentia-pytest:3.12 is missing" in issue for issue in report.unresolved_issues)


def test_generate_all_does_not_repair_missing_docker_image(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = make_workspace(tmp_path)

    def fake_which(name: str) -> str | None:
        return "/usr/bin/docker" if name == "docker" else None

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if command[:2] == ["/usr/bin/docker", "info"]:
            return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")
        if command[:3] == ["/usr/bin/docker", "image", "inspect"]:
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="missing")
        raise AssertionError(f"unexpected docker command: {command}")

    monkeypatch.setattr("shutil.which", fake_which)
    monkeypatch.setattr("subprocess.run", fake_run)
    result = generate_all(root, allow_native_execution=False, prefer_docker=True)
    assert not result.ok
    assert result.repair_attempts == 0
    assert TaskKind.REPAIR not in [task.task_kind for task in result.task_results]
    assert any("Docker image prudentia-pytest:3.12 is missing" in issue for issue in result.unresolved_issues)


def test_cli_smoke_path_create_generate_validate_report_export(tmp_path: Path) -> None:
    from prudentia.cli import app

    runner = CliRunner()
    create_result = runner.invoke(
        app,
        [
            "create",
            "--root",
            str(tmp_path),
            "--title",
            "Palindrome checker",
            "--course",
            "CS101",
            "--topic",
            "strings and functions",
            "--difficulty",
            "beginner",
        ],
    )
    assert create_result.exit_code == 0, create_result.output
    workspace_root = tmp_path / "palindrome-checker"
    assert workspace_root.exists()

    commands = [
        ["generate", "--all", "--allow-native-execution", "--workspace", str(workspace_root)],
        ["validate", "--allow-native-execution", "--workspace", str(workspace_root)],
        ["simulate", "--profiles", "weak,partial,misconception", "--allow-native-execution", "--workspace", str(workspace_root)],
        ["report", "--workspace", str(workspace_root)],
        ["approve", "--all", "--workspace", str(workspace_root)],
        ["export", "student", "--workspace", str(workspace_root)],
        ["export", "teacher", "--workspace", str(workspace_root)],
    ]
    for command in commands:
        result = runner.invoke(app, command)
        assert result.exit_code == 0, result.output
    assert (workspace_root / "reports/simulation_matrix.md").exists()
    assert (workspace_root / "exports/student/palindrome-checker-student.zip").exists()
    assert (workspace_root / "exports/teacher/palindrome-checker-teacher.zip").exists()
