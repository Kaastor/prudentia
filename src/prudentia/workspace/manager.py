from __future__ import annotations

import re
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from prudentia.core.jsonio import append_jsonl, read_json, write_json
from prudentia.core.models import CourseProfile, WorkflowState, WorkspaceMetadata
from prudentia.core.paths import PathSafetyError, normalize_workspace_root, safe_join
from prudentia.core.secrets import redact_text
from prudentia.core.time import utc_now_iso

WORKSPACE_DIRS = [
    "starter/src",
    "solution/src",
    "tests/visible",
    "tests/hidden",
    "simulations",
    "reports",
    "exports/student",
    "exports/teacher",
    ".codex",
    ".prudentia/context_manifests",
    ".prudentia/runs",
    ".prudentia/checkpoints",
    ".prudentia/export_manifests",
]

CURRENT_WORKSPACE_MARKER = ".prudentia-current-workspace.json"


@dataclass(frozen=True)
class Workspace:
    root: Path
    metadata: WorkspaceMetadata

    @property
    def id(self) -> str:
        return self.metadata.id

    @property
    def slug(self) -> str:
        return self.metadata.slug

    def path(self, relative_path: str | Path) -> Path:
        return safe_join(self.root, relative_path)


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", title.lower()).strip("-")
    slug = re.sub(r"-+", "-", slug)
    return slug or "assignment"


def create_workspace(
    base_dir: Path | str,
    *,
    title: str,
    course: str,
    topic: str,
    difficulty: str,
    level: str = "introductory",
    audience: str = "first-year undergraduate",
    estimated_minutes: int = 45,
    learning_objectives: list[str] | None = None,
    constraints: list[str] | None = None,
    slug: str | None = None,
    overwrite: bool = False,
) -> Workspace:
    base_path = normalize_workspace_root(base_dir)
    workspace_slug = slug or slugify(title)
    root = (base_path / workspace_slug).resolve()
    if root.exists() and any(root.iterdir()) and not overwrite:
        raise FileExistsError(f"Workspace already exists: {root}")
    root.mkdir(parents=True, exist_ok=True)

    metadata = WorkspaceMetadata(
        title=title.strip(),
        slug=workspace_slug,
        course=CourseProfile(name=course.strip(), level=level, audience=audience),
        assignment={
            "topic": topic.strip(),
            "difficulty": difficulty.strip(),
            "estimated_minutes": estimated_minutes,
            "learning_objectives": learning_objectives or [],
            "constraints": constraints or [],
        },
    )

    for directory in WORKSPACE_DIRS:
        safe_join(root, directory).mkdir(parents=True, exist_ok=True)

    write_metadata(root, metadata)
    write_codex_config(root)
    write_json(safe_join(root, ".prudentia/workflow_state.json"), WorkflowState(workspace_id=metadata.id))
    action_log = safe_join(root, ".prudentia/action_log.jsonl")
    action_log.touch(exist_ok=True)
    log_action(root, "workspace_created", {"title": title, "course": course, "topic": topic})
    workspace = Workspace(root=root, metadata=metadata)
    write_current_workspace_marker(base_path, workspace)
    return workspace


def write_metadata(root: Path, metadata: WorkspaceMetadata) -> None:
    metadata.touch()
    path = safe_join(root, "prudentia.yaml")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(metadata.model_dump(mode="json"), sort_keys=False), encoding="utf-8")


def load_workspace(root: Path | str) -> Workspace:
    root_path = normalize_workspace_root(root)
    metadata_path = safe_join(root_path, "prudentia.yaml")
    if not metadata_path.exists():
        raise FileNotFoundError(f"No prudentia.yaml found in {root_path}")
    metadata = WorkspaceMetadata.model_validate(yaml.safe_load(metadata_path.read_text(encoding="utf-8")))
    return Workspace(root=root_path, metadata=metadata)


def write_current_workspace_marker(base_dir: Path | str, workspace: Workspace) -> Path:
    base_path = normalize_workspace_root(base_dir)
    marker_path = safe_join(base_path, CURRENT_WORKSPACE_MARKER)
    try:
        workspace_path = workspace.root.relative_to(base_path).as_posix()
    except ValueError:
        workspace_path = str(workspace.root)
    write_json(
        marker_path,
        {
            "schema_version": "0.1",
            "workspace_id": workspace.id,
            "workspace_path": workspace_path,
            "updated_at": utc_now_iso(),
        },
    )
    return marker_path


def _current_workspace_from_marker(start: Path) -> Path | None:
    for candidate in [start, *start.parents]:
        marker_path = candidate / CURRENT_WORKSPACE_MARKER
        if not marker_path.exists():
            continue
        try:
            marker = read_json(marker_path)
            workspace_path = Path(str(marker["workspace_path"]))
        except Exception:
            continue
        root = workspace_path if workspace_path.is_absolute() else candidate / workspace_path
        if (root / "prudentia.yaml").exists():
            return root.resolve()
    return None


def find_workspace_root(start: Path | str) -> Path:
    current = normalize_workspace_root(start)
    if current.is_file():
        current = current.parent
    for candidate in [current, *current.parents]:
        if (candidate / "prudentia.yaml").exists():
            return candidate
    marked = _current_workspace_from_marker(current)
    if marked:
        return marked
    raise FileNotFoundError(f"Could not find prudentia.yaml at or above {current}")


def update_status(root: Path, **status_updates: Any) -> Workspace:
    workspace = load_workspace(root)
    for key, value in status_updates.items():
        if not hasattr(workspace.metadata.status, key):
            raise ValueError(f"Unknown status key: {key}")
        setattr(workspace.metadata.status, key, value)
    write_metadata(workspace.root, workspace.metadata)
    return load_workspace(workspace.root)


def write_codex_config(root: Path) -> None:
    config = """# Project-scoped Codex defaults for the Prudentia assignment workspace.
# Prudentia never writes user-level Codex configuration and never reads auth files.
approval_policy = "on-request"
sandbox_mode = "workspace-write"

[sandbox_workspace_write]
writable_roots = ["."]
network_access = false

[history]
persistence = "none"

[telemetry]
log_user_prompt = false
"""
    safe_join(root, ".codex/config.toml").write_text(config, encoding="utf-8")


def log_action(root: Path, action: str, payload: dict[str, Any] | None = None) -> None:
    entry = {
        "created_at": utc_now_iso(),
        "action": action,
        "payload": payload or {},
    }
    as_text = redact_text(str(entry))
    # Preserve dict shape while redacting common string values.
    entry["payload"] = {key: redact_text(str(value)) for key, value in entry["payload"].items()}
    entry["redacted_preview"] = as_text[:500]
    append_jsonl(safe_join(root, ".prudentia/action_log.jsonl"), entry)


def read_workflow_state(root: Path) -> WorkflowState:
    path = safe_join(root, ".prudentia/workflow_state.json")
    if not path.exists():
        workspace = load_workspace(root)
        state = WorkflowState(workspace_id=workspace.id)
        write_json(path, state)
        return state
    return WorkflowState.model_validate(read_json(path))


def write_workflow_state(root: Path, state: WorkflowState) -> None:
    state.updated_at = utc_now_iso()
    write_json(safe_join(root, ".prudentia/workflow_state.json"), state)


def record_progress(root: Path, event: dict[str, Any]) -> None:
    state = read_workflow_state(root)
    state.active_run_id = event.get("run_id", state.active_run_id)
    if event.get("event_kind") == "error":
        state.last_error = str(event.get("message"))
    state.progress_events.append(event)
    state.progress_events = state.progress_events[-200:]
    write_workflow_state(root, state)
    log_action(root, f"progress_{event.get('event_kind', 'event')}", event)


def clear_progress_error(root: Path) -> None:
    state = read_workflow_state(root)
    state.last_error = None
    write_workflow_state(root, state)


def checkpoint_workspace(root: Path, label: str) -> Path:
    workspace = load_workspace(root)
    timestamp = utc_now_iso().replace(":", "").replace("-", "").replace("Z", "")
    checkpoint_path = safe_join(root, f".prudentia/checkpoints/{timestamp}-{label}.zip")
    excluded_prefixes = (".prudentia/runs/", "exports/")
    with zipfile.ZipFile(checkpoint_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            if rel == checkpoint_path.relative_to(root).as_posix():
                continue
            if rel.startswith(excluded_prefixes):
                continue
            archive.write(path, rel)
    log_action(root, "checkpoint_created", {"label": label, "path": checkpoint_path.name, "workspace_id": workspace.id})
    return checkpoint_path


def clean_runs(root: Path) -> int:
    runs_dir = safe_join(root, ".prudentia/runs")
    count = 0
    for child in runs_dir.iterdir() if runs_dir.exists() else []:
        if child.is_dir():
            shutil.rmtree(child)
            count += 1
        elif child.is_file():
            child.unlink()
            count += 1
    log_action(root, "runs_cleaned", {"count": count})
    return count


def assert_workspace_path(root: Path, relative_path: str | Path) -> Path:
    try:
        return safe_join(root, relative_path)
    except PathSafetyError:
        raise
