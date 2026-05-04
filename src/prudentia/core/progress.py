from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from prudentia.core.time import utc_now_iso

ProgressKind = Literal[
    "run_start",
    "codex_task_start",
    "codex_task_finish",
    "validation_start",
    "validation_finish",
    "export_start",
    "export_finish",
    "repair_start",
    "error",
]


class ProgressEvent(BaseModel):
    run_id: str
    workspace_id: str
    event_kind: ProgressKind
    message: str
    created_at: str = Field(default_factory=utc_now_iso)
    payload: dict[str, Any] | None = None


def new_run_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"
