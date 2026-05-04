from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from prudentia.core.jsonio import write_json
from prudentia.core.models import ArtifactStatus
from prudentia.core.paths import matches_any, relative_to_root
from prudentia.core.progress import ProgressEvent, new_run_id
from prudentia.core.time import utc_now_iso
from prudentia.export.scanner import (
    ExportFinding,
    ExportSafetyError,
    ExportScanResult,
    TEACHER_FORBIDDEN_PATHS,
    scan_export_files,
)
from prudentia.workspace.manager import clear_progress_error, load_workspace, record_progress, update_status

ExportKind = Literal["student", "teacher"]
APPROVAL_STATUS_FIELDS = ["brief", "starter", "solution", "tests", "rubric"]


class ExportManifest(BaseModel):
    schema_version: str = "0.1"
    export_kind: ExportKind
    workspace_id: str
    created_at: str = Field(default_factory=utc_now_iso)
    status: str
    zip_path: str | None = None
    included_files: list[str]
    excluded_files: list[str]
    scanner_result: ExportScanResult
    block_reasons: list[str] = Field(default_factory=list)


class ExportReadinessError(RuntimeError):
    def __init__(self, message: str, manifest: ExportManifest):
        super().__init__(message)
        self.manifest = manifest


def _is_file(path: Path) -> bool:
    return path.exists() and path.is_file()


def _collect_under(root: Path, relative_dir: str, *, exclude_globs: list[str] | None = None) -> list[Path]:
    directory = root / relative_dir
    if not directory.exists():
        return []
    files: list[Path] = []
    for path in directory.rglob("*"):
        if not path.is_file():
            continue
        rel = relative_to_root(root, path)
        if exclude_globs and matches_any(rel, exclude_globs):
            continue
        files.append(path)
    return files


def student_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for relative in ["brief.md", "README.student.md", "pyproject.toml"]:
        path = root / relative
        if _is_file(path):
            files.append(path)
    files.extend(_collect_under(root, "starter"))
    files.extend(_collect_under(root, "tests/visible"))
    return sorted(set(files), key=lambda path: relative_to_root(root, path))


def teacher_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for relative in ["brief.md", "README.student.md", "rubric.md", "pyproject.toml", "prudentia.yaml"]:
        path = root / relative
        if _is_file(path):
            files.append(path)
    for directory in ["starter", "solution", "tests", "simulations", "reports"]:
        files.extend(_collect_under(root, directory, exclude_globs=TEACHER_FORBIDDEN_PATHS))
    return sorted(set(files), key=lambda path: relative_to_root(root, path))


def all_workspace_files(root: Path) -> set[str]:
    return {relative_to_root(root, path) for path in root.rglob("*") if path.is_file()}


def write_manifest(root: Path, manifest: ExportManifest) -> Path:
    timestamp = manifest.created_at.replace(":", "").replace("-", "").replace("Z", "")
    path = root / ".prudentia" / "export_manifests" / f"{timestamp}-{manifest.export_kind}.json"
    write_json(path, manifest)
    return path


def export_readiness_reasons(root: Path) -> list[str]:
    workspace = load_workspace(root)
    status = workspace.metadata.status
    reasons: list[str] = []
    for field in APPROVAL_STATUS_FIELDS:
        if getattr(status, field) != ArtifactStatus.APPROVED:
            reasons.append(f"{field} must be approved before export.")
    if status.validation != ArtifactStatus.PASSED:
        reasons.append("validation must pass before export.")
    return reasons


def _blocked_manifest(
    *,
    export_kind: ExportKind,
    workspace_id: str,
    included: list[str],
    excluded: list[str],
    block_reasons: list[str],
    scanner_result: ExportScanResult | None = None,
) -> ExportManifest:
    findings = [ExportFinding(path=".", reason=reason, kind="readiness") for reason in block_reasons]
    return ExportManifest(
        export_kind=export_kind,
        workspace_id=workspace_id,
        status="blocked",
        zip_path=None,
        included_files=included,
        excluded_files=excluded,
        scanner_result=scanner_result or ExportScanResult(export_kind=export_kind, ok=False, findings=findings),
        block_reasons=block_reasons,
    )


def package_export(root: Path | str, export_kind: ExportKind) -> ExportManifest:
    workspace = load_workspace(root)
    run_id = new_run_id(f"export-{export_kind}")
    record_progress(
        workspace.root,
        ProgressEvent(
            run_id=run_id,
            workspace_id=workspace.id,
            event_kind="export_start",
            message=f"{export_kind} export started.",
            payload={"export_kind": export_kind},
        ).model_dump(mode="json"),
    )
    clear_progress_error(workspace.root)
    files = student_files(workspace.root) if export_kind == "student" else teacher_files(workspace.root)
    included = [relative_to_root(workspace.root, path) for path in files]
    excluded = sorted(all_workspace_files(workspace.root) - set(included))
    readiness_reasons = export_readiness_reasons(workspace.root)
    if readiness_reasons:
        manifest = _blocked_manifest(
            export_kind=export_kind,
            workspace_id=workspace.id,
            included=included,
            excluded=excluded,
            block_reasons=readiness_reasons,
        )
        write_manifest(workspace.root, manifest)
        update_status(workspace.root, export=ArtifactStatus.NOT_READY)
        record_progress(
            workspace.root,
            ProgressEvent(
                run_id=run_id,
                workspace_id=workspace.id,
                event_kind="error",
                message=f"{export_kind} export blocked until artifacts are approved and validation passes.",
                payload=manifest.model_dump(mode="json"),
            ).model_dump(mode="json"),
        )
        raise ExportReadinessError(f"{export_kind} export is not ready", manifest)
    scan = scan_export_files(workspace.root, files, export_kind)
    if not scan.ok:
        manifest = _blocked_manifest(
            export_kind=export_kind,
            workspace_id=workspace.id,
            included=included,
            excluded=excluded,
            scanner_result=scan,
            block_reasons=["Safety scanner blocked export."],
        )
        write_manifest(workspace.root, manifest)
        update_status(workspace.root, export=ArtifactStatus.NOT_READY)
        record_progress(
            workspace.root,
            ProgressEvent(
                run_id=run_id,
                workspace_id=workspace.id,
                event_kind="error",
                message=f"{export_kind} export blocked by safety scanner.",
                payload=manifest.model_dump(mode="json"),
            ).model_dump(mode="json"),
        )
        raise ExportSafetyError(f"{export_kind} export blocked by safety scanner", scan)

    zip_dir = workspace.path(f"exports/{export_kind}")
    zip_dir.mkdir(parents=True, exist_ok=True)
    zip_path = zip_dir / f"{workspace.slug}-{export_kind}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, relative_to_root(workspace.root, path))
    manifest = ExportManifest(
        export_kind=export_kind,
        workspace_id=workspace.id,
        status="written",
        zip_path=relative_to_root(workspace.root, zip_path),
        included_files=included,
        excluded_files=excluded,
        scanner_result=scan,
    )
    write_manifest(workspace.root, manifest)
    update_status(workspace.root, export=ArtifactStatus.READY)
    clear_progress_error(workspace.root)
    record_progress(
        workspace.root,
        ProgressEvent(
            run_id=run_id,
            workspace_id=workspace.id,
            event_kind="export_finish",
            message=f"{export_kind} export written.",
            payload=manifest.model_dump(mode="json"),
        ).model_dump(mode="json"),
    )
    return manifest
