from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from prudentia.codex.manifests import create_context_manifest
from prudentia.core.doctor import run_doctor
from prudentia.core.models import ArtifactStatus, TaskKind
from prudentia.core.paths import PathSafetyError
from prudentia.export.packager import ExportReadinessError, package_export
from prudentia.export.scanner import ExportSafetyError
from prudentia.generation.pipeline import generate_all, generate_steps
from prudentia.reporting.reports import refresh_reports
from prudentia.simulation.service import simulate_profiles
from prudentia.validation.service import validate_workspace
from prudentia.workspace.manager import (
    create_workspace,
    find_workspace_root,
    load_workspace,
    read_workflow_state,
    update_status,
    write_current_workspace_marker,
)

WEB_DIR = Path(__file__).resolve().parents[1] / "web"


class CreateWorkspaceRequest(BaseModel):
    root: str = Field(default_factory=lambda: os.getcwd())
    title: str
    course: str
    topic: str
    difficulty: str
    estimated_minutes: int = 45
    learning_objectives: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)


class OpenWorkspaceRequest(BaseModel):
    path: str


class GenerateRequest(BaseModel):
    workspace: str
    step: str = "all"
    use_codex: bool = False
    allow_native_execution: bool = False


class ValidateRequest(BaseModel):
    workspace: str
    allow_native_execution: bool = False


class SimulateRequest(BaseModel):
    workspace: str
    profiles: str = "weak,partial,misconception"
    allow_native_execution: bool = False


class ReportRequest(BaseModel):
    workspace: str


class ExportRequest(BaseModel):
    workspace: str


class ApproveRequest(BaseModel):
    workspace: str
    artifact: str


def _load(path: str):
    try:
        return load_workspace(find_workspace_root(Path(path)))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _workspace_status(path: str) -> dict[str, Any]:
    ws = _load(path)
    artifacts = {
        "brief.md": ws.path("brief.md").exists(),
        "README.student.md": ws.path("README.student.md").exists(),
        "starter/src/assignment.py": ws.path("starter/src/assignment.py").exists(),
        "solution/src/assignment.py": ws.path("solution/src/assignment.py").exists(),
        "tests/visible/test_basic.py": ws.path("tests/visible/test_basic.py").exists(),
        "tests/hidden/test_edge_cases.py": ws.path("tests/hidden/test_edge_cases.py").exists(),
        "rubric.md": ws.path("rubric.md").exists(),
        "reports/validation_report.json": ws.path("reports/validation_report.json").exists(),
        "reports/simulation_matrix.md": ws.path("reports/simulation_matrix.md").exists(),
    }
    return {
        "workspace": str(ws.root),
        "metadata": ws.metadata.model_dump(mode="json"),
        "artifacts": artifacts,
    }


def create_app() -> FastAPI:
    app = FastAPI(title="Prudentia MVP", version="0.1.0")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "preselected_workspace": os.environ.get("PRUDENTIA_WORKSPACE", "")}

    @app.get("/api/doctor")
    def doctor() -> dict[str, Any]:
        return run_doctor().model_dump(mode="json")

    @app.post("/api/workspaces")
    def create_workspace_endpoint(request: CreateWorkspaceRequest) -> dict[str, Any]:
        try:
            ws = create_workspace(
                request.root,
                title=request.title,
                course=request.course,
                topic=request.topic,
                difficulty=request.difficulty,
                estimated_minutes=request.estimated_minutes,
                learning_objectives=request.learning_objectives,
                constraints=request.constraints,
            )
            return _workspace_status(str(ws.root))
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/workspace/open")
    def open_workspace_endpoint(request: OpenWorkspaceRequest) -> dict[str, Any]:
        ws = _load(request.path)
        write_current_workspace_marker(ws.root.parent, ws)
        return _workspace_status(str(ws.root))

    @app.get("/api/workspace/status")
    def status(workspace: str = Query(...)) -> dict[str, Any]:
        return _workspace_status(workspace)

    @app.get("/api/progress")
    def progress(workspace: str = Query(...)) -> dict[str, Any]:
        ws = _load(workspace)
        return read_workflow_state(ws.root).model_dump(mode="json")

    @app.get("/api/context")
    def context(workspace: str = Query(...), task_kind: TaskKind = Query(TaskKind.BRIEF)) -> dict[str, Any]:
        ws = _load(workspace)
        manifest = create_context_manifest(ws, task_kind)
        return manifest.model_dump(mode="json")

    @app.get("/api/artifact")
    def artifact(workspace: str = Query(...), path: str = Query(...)) -> dict[str, str]:
        ws = _load(workspace)
        try:
            artifact_path = ws.path(path)
        except PathSafetyError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if not artifact_path.exists() or not artifact_path.is_file():
            return {"path": path, "content": ""}
        return {"path": path, "content": artifact_path.read_text(encoding="utf-8", errors="replace")}

    @app.post("/api/generate")
    def generate(request: GenerateRequest) -> dict[str, Any]:
        ws = _load(request.workspace)
        try:
            if request.step == "all":
                result = generate_all(
                    ws.root,
                    use_live_codex=request.use_codex,
                    allow_native_execution=request.allow_native_execution,
                    prefer_docker=not request.allow_native_execution,
                )
            else:
                result = generate_steps(ws.root, [TaskKind(request.step)], use_live_codex=request.use_codex)
            return result.model_dump(mode="json")
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/validate")
    def validate(request: ValidateRequest) -> dict[str, Any]:
        ws = _load(request.workspace)
        try:
            result = validate_workspace(
                ws.root, allow_native_execution=request.allow_native_execution, prefer_docker=not request.allow_native_execution
            )
            return result.model_dump(mode="json")
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/simulate")
    def simulate(request: SimulateRequest) -> dict[str, Any]:
        ws = _load(request.workspace)
        try:
            result = simulate_profiles(
                ws.root,
                profiles=request.profiles,
                allow_native_execution=request.allow_native_execution,
                prefer_docker=not request.allow_native_execution,
            )
            return result.model_dump(mode="json")
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/report")
    def report(request: ReportRequest) -> dict[str, str]:
        ws = _load(request.workspace)
        path = refresh_reports(ws.root)
        return {"path": str(path)}

    @app.post("/api/export/{kind}")
    def export(kind: str, request: ExportRequest) -> dict[str, Any]:
        if kind not in {"student", "teacher"}:
            raise HTTPException(status_code=400, detail="kind must be student or teacher")
        ws = _load(request.workspace)
        try:
            manifest = package_export(ws.root, kind)  # type: ignore[arg-type]
            return manifest.model_dump(mode="json")
        except ExportReadinessError as exc:
            raise HTTPException(status_code=400, detail=exc.manifest.model_dump(mode="json")) from exc
        except ExportSafetyError as exc:
            raise HTTPException(status_code=400, detail=exc.scan_result.model_dump(mode="json")) from exc

    @app.post("/api/approve")
    def approve(request: ApproveRequest) -> dict[str, Any]:
        artifact_to_status = {
            "brief": "brief",
            "starter": "starter",
            "solution": "solution",
            "tests": "tests",
            "rubric": "rubric",
        }
        if request.artifact not in artifact_to_status:
            raise HTTPException(status_code=400, detail="Unknown artifact status")
        ws = _load(request.workspace)
        updated = update_status(ws.root, **{artifact_to_status[request.artifact]: ArtifactStatus.APPROVED})
        return updated.metadata.status.model_dump(mode="json")

    return app
