from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys

from prudentia.codex.adapter import LiveCodexAdapter
from prudentia.core.models import DoctorCheck, DoctorReport


def _docker_detail() -> tuple[bool, str]:
    docker = shutil.which("docker")
    if not docker:
        return False, "docker executable not found"
    try:
        completed = subprocess.run([docker, "info"], capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"docker executable found but daemon check failed: {exc}"
    if completed.returncode != 0:
        return False, (completed.stderr or completed.stdout or "docker info failed").strip()[:300]
    return True, "Docker daemon is reachable. Build docker/prudentia-pytest.Dockerfile as prudentia-pytest:3.12 for default sandbox runs."


def _docker_image_detail() -> tuple[bool, str]:
    image = os.environ.get("PRUDENTIA_DOCKER_IMAGE", "prudentia-pytest:3.12")
    docker = shutil.which("docker")
    if not docker:
        return False, f"Docker image {image} cannot be checked because docker is unavailable."
    try:
        completed = subprocess.run([docker, "image", "inspect", image], capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"Docker image check failed for {image}: {exc}"
    if completed.returncode != 0:
        return False, f"Docker image {image} is missing. Build it with: docker build -f docker/prudentia-pytest.Dockerfile -t {image} ."
    return True, f"Docker image {image} is available for default sandbox runs."


def run_doctor() -> DoctorReport:
    checks: list[DoctorCheck] = []
    py_ok = sys.version_info >= (3, 12)
    checks.append(DoctorCheck(name="python", ok=py_ok, detail=f"Python {sys.version.split()[0]}"))
    checks.append(
        DoctorCheck(
            name="pytest",
            ok=importlib.util.find_spec("pytest") is not None,
            detail="pytest import available" if importlib.util.find_spec("pytest") else "pytest not importable",
        )
    )
    checks.append(
        DoctorCheck(
            name="pytest-json-report",
            ok=importlib.util.find_spec("pytest_jsonreport") is not None,
            detail="pytest-json-report import available"
            if importlib.util.find_spec("pytest_jsonreport")
            else "pytest-json-report not importable",
        )
    )
    docker_ok, docker_detail = _docker_detail()
    checks.append(DoctorCheck(name="docker", ok=docker_ok, detail=docker_detail))
    image_ok, image_detail = _docker_image_detail()
    checks.append(DoctorCheck(name="docker-image", ok=image_ok, detail=image_detail))
    codex = LiveCodexAdapter().readiness()
    checks.append(DoctorCheck(name="codex", ok=codex.available, detail=f"{codex.mode}: {codex.detail}. {codex.setup_guidance}"))
    return DoctorReport(checks=checks)
