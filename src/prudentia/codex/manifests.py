from __future__ import annotations

from uuid import uuid4

from pydantic import BaseModel, Field

from prudentia.core.jsonio import write_json
from prudentia.core.models import FileRole, TaskKind
from prudentia.core.paths import matches_any, relative_to_root, safe_join
from prudentia.core.time import utc_now_iso
from prudentia.workspace.manager import Workspace, log_action


class ManifestFile(BaseModel):
    path: str
    reason: str
    role: FileRole


class ContextManifest(BaseModel):
    schema_version: str = "0.1"
    manifest_id: str = Field(default_factory=lambda: str(uuid4()))
    workspace_id: str
    task_kind: TaskKind
    created_at: str = Field(default_factory=utc_now_iso)
    included_files: list[ManifestFile]
    excluded_globs: list[str]
    allowed_write_globs: list[str]
    privacy_warnings: list[str]


def role_for_path(path: str) -> FileRole:
    if path == "prudentia.yaml" or path.startswith(".codex/"):
        return FileRole.METADATA
    if path.startswith("solution/") or path.startswith("tests/hidden/") or path.startswith("simulations/"):
        return FileRole.TEACHER_ONLY
    if path.startswith("tests/"):
        return FileRole.TEST
    if path.startswith("reports/"):
        return FileRole.REPORT
    return FileRole.STUDENT_VISIBLE


def allowed_writes_for_task(task_kind: TaskKind) -> list[str]:
    mapping = {
        TaskKind.PLANNING: [".prudentia/codex_status.json"],
        TaskKind.BRIEF: ["brief.md", "README.student.md", "pyproject.toml", ".prudentia/codex_status.json"],
        TaskKind.STARTER: ["starter/**", ".prudentia/codex_status.json"],
        TaskKind.SOLUTION: ["solution/**", ".prudentia/codex_status.json"],
        TaskKind.TESTS: ["tests/visible/**", "tests/hidden/**", ".prudentia/codex_status.json"],
        TaskKind.REPAIR: ["solution/**", "tests/visible/**", "tests/hidden/**", ".prudentia/codex_status.json"],
        TaskKind.RUBRIC: ["rubric.md", ".prudentia/codex_status.json"],
        TaskKind.SIMULATIONS: ["simulations/**", ".prudentia/codex_status.json"],
        TaskKind.REPORT: ["reports/**", ".prudentia/codex_status.json"],
        TaskKind.QUALITY_REVIEW: ["reports/teacher_report.md", ".prudentia/codex_status.json"],
    }
    return mapping[task_kind]


def reason_for_path(path: str, task_kind: TaskKind) -> str:
    if path == "prudentia.yaml":
        return "Workspace metadata and policy source of truth."
    if task_kind == TaskKind.REPAIR:
        return "Evidence for bounded repair after validation."
    if path.startswith("tests/"):
        return "Test contract relevant to artifact quality."
    if path.startswith("solution/"):
        return "Teacher-only reference for validation or repair."
    if path.startswith("starter/"):
        return "Student-facing starter artifact under review."
    if path.startswith("reports/"):
        return "Generated report evidence."
    return "Assignment artifact relevant to the requested task."


def create_context_manifest(workspace: Workspace, task_kind: TaskKind) -> ContextManifest:
    policy = workspace.metadata.policy
    included: list[ManifestFile] = []
    excluded_globs = sorted(set(policy.never_send + ["exports/**", ".prudentia/action_log.jsonl"]))
    for path in sorted(workspace.root.rglob("*")):
        if not path.is_file():
            continue
        rel = relative_to_root(workspace.root, path)
        if matches_any(rel, excluded_globs):
            continue
        if not matches_any(rel, policy.ai_context_allowlist) and rel != "prudentia.yaml":
            continue
        included.append(ManifestFile(path=rel, reason=reason_for_path(rel, task_kind), role=role_for_path(rel)))
    manifest = ContextManifest(
        workspace_id=workspace.id,
        task_kind=task_kind,
        included_files=included,
        excluded_globs=excluded_globs,
        allowed_write_globs=allowed_writes_for_task(task_kind),
        privacy_warnings=[
            "Never include real student data in MVP Codex context.",
            "Student-facing files must not contain solution files or hidden tests.",
            "Prudentia never reads ~/.codex/auth.json or asks for OpenAI credentials.",
        ],
    )
    manifest_path = safe_join(
        workspace.root,
        f".prudentia/context_manifests/{manifest.created_at.replace(':', '').replace('-', '').replace('Z', '')}-{task_kind.value}.json",
    )
    write_json(manifest_path, manifest)
    log_action(workspace.root, "context_manifest_created", {"task_kind": task_kind.value, "manifest_id": manifest.manifest_id})
    return manifest


def manifest_relative_path(workspace: Workspace, manifest: ContextManifest) -> str:
    manifest_dir = safe_join(workspace.root, ".prudentia/context_manifests")
    for path in manifest_dir.glob(f"*-{manifest.task_kind.value}.json"):
        try:
            import json

            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("manifest_id") == manifest.manifest_id:
                return relative_to_root(workspace.root, path)
        except Exception:
            continue
    return ".prudentia/context_manifests"
