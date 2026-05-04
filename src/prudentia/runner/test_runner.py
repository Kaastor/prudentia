from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from prudentia.core.jsonio import write_json
from prudentia.core.paths import matches_any, safe_join
from prudentia.core.progress import new_run_id
from prudentia.core.time import utc_now_iso
from prudentia.workspace.manager import load_workspace, log_action

ExecutionMode = Literal["docker", "native"]
SubmissionTarget = Literal["solution", "weak", "partial", "misconception"]

COPY_IGNORE_GLOBS = [
    ".prudentia/runs/**",
    "exports/**",
    "__pycache__/**",
    ".pytest_cache/**",
    "*.pyc",
]


class PytestRunResult(BaseModel):
    run_id: str
    workspace_id: str
    target: SubmissionTarget
    mode: ExecutionMode
    run_dir: str
    workspace_copy: str
    stdout_path: str
    stderr_path: str
    exit_code: int
    pytest_report_path: str
    metadata_path: str
    started_at: str
    finished_at: str
    command: list[str]
    ok: bool


class NativeExecutionNotAllowed(RuntimeError):
    pass


class DockerUnavailable(RuntimeError):
    pass


def target_source_path(target: SubmissionTarget) -> str:
    if target == "solution":
        return "solution/src"
    return f"simulations/{target}/src"


def stage_target_submission(workspace_copy: Path, target: SubmissionTarget) -> None:
    source = workspace_copy / target_source_path(target) / "assignment.py"
    destination = workspace_copy / "starter" / "src" / "assignment.py"
    if not source.exists():
        raise FileNotFoundError(f"Submission target is missing: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)


def copy_workspace_for_run(source_root: Path, workspace_copy: Path) -> None:
    def ignore(directory: str, names: list[str]) -> set[str]:
        ignored: set[str] = set()
        dir_path = Path(directory)
        for name in names:
            candidate = dir_path / name
            try:
                rel = candidate.relative_to(source_root).as_posix()
            except ValueError:
                rel = name
            if matches_any(rel, COPY_IGNORE_GLOBS) or matches_any(rel + "/", COPY_IGNORE_GLOBS):
                ignored.add(name)
        return ignored

    shutil.copytree(source_root, workspace_copy, ignore=ignore, dirs_exist_ok=False)


def run_pytest(
    root: Path | str,
    *,
    target: SubmissionTarget = "solution",
    allow_native_execution: bool = False,
    prefer_docker: bool = True,
) -> PytestRunResult:
    workspace = load_workspace(root)
    run_id = new_run_id(f"pytest-{target}")
    run_dir = safe_join(workspace.root, f".prudentia/runs/{run_id}")
    workspace_copy = run_dir / "workspace-copy"
    run_dir.mkdir(parents=True, exist_ok=False)
    copy_workspace_for_run(workspace.root, workspace_copy)
    stage_target_submission(workspace_copy, target)

    if prefer_docker:
        try:
            return _run_docker(workspace.root, workspace.id, run_id, run_dir, workspace_copy, target)
        except DockerUnavailable:
            if not allow_native_execution:
                raise
    if not allow_native_execution:
        raise NativeExecutionNotAllowed("Native pytest execution requires --allow-native-execution.")
    return _run_native(workspace.root, workspace.id, run_id, run_dir, workspace_copy, target)


def _metadata(
    *,
    workspace_root: Path,
    workspace_id: str,
    run_id: str,
    run_dir: Path,
    workspace_copy: Path,
    target: SubmissionTarget,
    mode: ExecutionMode,
    command: list[str],
    started_at: str,
    finished_at: str,
    exit_code: int,
) -> dict[str, object]:
    return {
        "schema_version": "0.1",
        "workspace_id": workspace_id,
        "run_id": run_id,
        "target": target,
        "mode": mode,
        "workspace_root": str(workspace_root),
        "workspace_copy": str(workspace_copy),
        "network_disabled": mode == "docker",
        "source_workspace_writes": False,
        "workspace_copy_readonly": mode == "docker",
        "command": command,
        "started_at": started_at,
        "finished_at": finished_at,
        "exit_code": exit_code,
    }


def _complete_result(
    *,
    workspace_root: Path,
    workspace_id: str,
    run_id: str,
    run_dir: Path,
    workspace_copy: Path,
    target: SubmissionTarget,
    mode: ExecutionMode,
    command: list[str],
    started_at: str,
    finished_at: str,
    exit_code: int,
) -> PytestRunResult:
    metadata_path = run_dir / "run_metadata.json"
    write_json(
        metadata_path,
        _metadata(
            workspace_root=workspace_root,
            workspace_id=workspace_id,
            run_id=run_id,
            run_dir=run_dir,
            workspace_copy=workspace_copy,
            target=target,
            mode=mode,
            command=command,
            started_at=started_at,
            finished_at=finished_at,
            exit_code=exit_code,
        ),
    )
    (run_dir / "exit_code.txt").write_text(str(exit_code), encoding="utf-8")
    if not (run_dir / "pytest_report.json").exists():
        write_json(run_dir / "pytest_report.json", {"created": utc_now_iso(), "summary": {}, "tests": []})
    result = PytestRunResult(
        run_id=run_id,
        workspace_id=workspace_id,
        target=target,
        mode=mode,
        run_dir=str(run_dir),
        workspace_copy=str(workspace_copy),
        stdout_path=str(run_dir / "stdout.txt"),
        stderr_path=str(run_dir / "stderr.txt"),
        exit_code=exit_code,
        pytest_report_path=str(run_dir / "pytest_report.json"),
        metadata_path=str(metadata_path),
        started_at=started_at,
        finished_at=finished_at,
        command=command,
        ok=exit_code == 0,
    )
    log_action(workspace_root, "pytest_run_finished", result.model_dump(mode="json"))
    return result


def _run_native(
    workspace_root: Path,
    workspace_id: str,
    run_id: str,
    run_dir: Path,
    workspace_copy: Path,
    target: SubmissionTarget,
) -> PytestRunResult:
    started_at = utc_now_iso()
    report_path = run_dir / "pytest_report.json"
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-p",
        "pytest_jsonreport.plugin",
        "tests/visible",
        "tests/hidden",
        "--import-mode=importlib",
        "--json-report",
        f"--json-report-file={report_path}",
    ]
    import pytest

    src_path = workspace_copy / "starter" / "src"
    old_cwd = Path.cwd()
    old_path = list(sys.path)
    old_env = os.environ.get("PYTEST_DISABLE_PLUGIN_AUTOLOAD")
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    for module_name in ["assignment", "test_basic", "test_edge_cases"]:
        sys.modules.pop(module_name, None)
    try:
        os.chdir(workspace_copy)
        sys.path.insert(0, str(src_path))
        os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
            exit_code = int(
                pytest.main(
                    [
                        "-p",
                        "pytest_jsonreport.plugin",
                        "tests/visible",
                        "tests/hidden",
                        "--import-mode=importlib",
                        "--json-report",
                        f"--json-report-file={report_path}",
                    ]
                )
            )
    finally:
        for module_name in ["assignment", "test_basic", "test_edge_cases"]:
            sys.modules.pop(module_name, None)
        sys.path[:] = old_path
        os.chdir(old_cwd)
        if old_env is None:
            os.environ.pop("PYTEST_DISABLE_PLUGIN_AUTOLOAD", None)
        else:
            os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = old_env
    (run_dir / "stdout.txt").write_text(stdout_buffer.getvalue(), encoding="utf-8")
    (run_dir / "stderr.txt").write_text(stderr_buffer.getvalue(), encoding="utf-8")
    return _complete_result(
        workspace_root=workspace_root,
        workspace_id=workspace_id,
        run_id=run_id,
        run_dir=run_dir,
        workspace_copy=workspace_copy,
        target=target,
        mode="native",
        command=command,
        started_at=started_at,
        finished_at=utc_now_iso(),
        exit_code=exit_code,
    )


def _docker_available() -> bool:
    docker = shutil.which("docker")
    if not docker:
        return False
    try:
        completed = subprocess.run([docker, "info"], capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return completed.returncode == 0


def _docker_image_available(image: str) -> bool:
    docker = shutil.which("docker")
    if not docker:
        return False
    try:
        completed = subprocess.run([docker, "image", "inspect", image], capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return completed.returncode == 0


def _run_docker(
    workspace_root: Path,
    workspace_id: str,
    run_id: str,
    run_dir: Path,
    workspace_copy: Path,
    target: SubmissionTarget,
) -> PytestRunResult:
    if not _docker_available():
        raise DockerUnavailable("Docker is unavailable. Use --allow-native-execution only after accepting local execution risk.")
    image = os.environ.get("PRUDENTIA_DOCKER_IMAGE", "prudentia-pytest:3.12")
    if not _docker_image_available(image):
        raise DockerUnavailable(
            f"Docker image {image} is missing. Build it with: docker build -f docker/prudentia-pytest.Dockerfile -t {image} ."
        )
    started_at = utc_now_iso()
    target_src = "/workspace/starter/src"
    command = [
        "docker",
        "run",
        "--rm",
        "--pull",
        "never",
        "--network",
        "none",
        "-v",
        f"{workspace_copy}:/workspace:ro",
        "-v",
        f"{run_dir}:/run_results:rw",
        "-w",
        "/workspace",
        "-e",
        f"PYTHONPATH={target_src}",
        "-e",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1",
        "-e",
        "PYTHONPYCACHEPREFIX=/run_results/pycache",
        "-e",
        "TMPDIR=/run_results/tmp",
        image,
        "python",
        "-m",
        "pytest",
        "-p",
        "pytest_jsonreport.plugin",
        "tests/visible",
        "tests/hidden",
        "-o",
        "cache_dir=/run_results/.pytest_cache",
        "--import-mode=importlib",
        "--json-report",
        "--json-report-file=/run_results/pytest_report.json",
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = target_src
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env["PYTHONPYCACHEPREFIX"] = "/run_results/pycache"
    env["TMPDIR"] = "/run_results/tmp"
    (run_dir / "tmp").mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(command, env=env, capture_output=True, text=True, check=False)
    (run_dir / "stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (run_dir / "stderr.txt").write_text(completed.stderr, encoding="utf-8")
    # Docker does not receive PYTHONPATH through host env after image command boundary. If the image entrypoint
    # ignores env, this fallback records actionable output instead of mutating the source workspace.
    if completed.returncode != 0 and not (run_dir / "pytest_report.json").exists():
        try:
            json.loads((run_dir / "stdout.txt").read_text(encoding="utf-8"))
        except Exception:
            pass
    return _complete_result(
        workspace_root=workspace_root,
        workspace_id=workspace_id,
        run_id=run_id,
        run_dir=run_dir,
        workspace_copy=workspace_copy,
        target=target,
        mode="docker",
        command=command,
        started_at=started_at,
        finished_at=utc_now_iso(),
        exit_code=completed.returncode,
    )
