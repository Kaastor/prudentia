from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Literal

from pydantic import BaseModel, Field

from prudentia.core.paths import matches_any, relative_to_root

ExportKind = Literal["student", "teacher"]

STUDENT_FORBIDDEN_PATHS = [
    "solution/**",
    "tests/hidden/**",
    "simulations/**",
    "reports/**",
    "exports/**",
    ".prudentia/**",
    ".codex/**",
]

STUDENT_FORBIDDEN_CONTENT = [
    re.compile(r"REFERENCE SOLUTION", re.IGNORECASE),
    re.compile(r"hidden\s+test", re.IGNORECASE),
    re.compile(r"tests/hidden", re.IGNORECASE),
    re.compile(r"solution/src", re.IGNORECASE),
    re.compile(r"solution/", re.IGNORECASE),
]

TEACHER_FORBIDDEN_PATHS = [
    "exports/**",
    ".codex/**",
    ".prudentia/action_log.jsonl",
    ".prudentia/context_manifests/**",
    "**/.DS_Store",
    "**/*.tmp",
    "**/*.swp",
    "**/__pycache__/**",
    "**/*.pyc",
]

TEACHER_FORBIDDEN_CONTENT = [
    re.compile(r"OPENAI_API_KEY", re.IGNORECASE),
    re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"session[_\- ]?token", re.IGNORECASE),
    re.compile(r"auth\.json", re.IGNORECASE),
    re.compile(r"Bearer\s+[A-Za-z0-9._\-]{8,}", re.IGNORECASE),
]


class ExportFinding(BaseModel):
    path: str
    reason: str
    kind: str


class ExportScanResult(BaseModel):
    export_kind: ExportKind
    ok: bool
    findings: list[ExportFinding] = Field(default_factory=list)


class ExportSafetyError(RuntimeError):
    def __init__(self, message: str, scan_result: ExportScanResult):
        super().__init__(message)
        self.scan_result = scan_result


def scan_export_files(root: Path, files: Iterable[Path], export_kind: ExportKind) -> ExportScanResult:
    findings: list[ExportFinding] = []
    path_patterns = STUDENT_FORBIDDEN_PATHS if export_kind == "student" else TEACHER_FORBIDDEN_PATHS
    content_patterns = STUDENT_FORBIDDEN_CONTENT if export_kind == "student" else TEACHER_FORBIDDEN_CONTENT
    for path in files:
        rel = relative_to_root(root, path)
        if matches_any(rel, path_patterns):
            findings.append(ExportFinding(path=rel, reason="Forbidden path for export package.", kind="path"))
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for pattern in content_patterns:
            if pattern.search(text):
                findings.append(ExportFinding(path=rel, reason=f"Forbidden content marker matched: {pattern.pattern}", kind="content"))
    return ExportScanResult(export_kind=export_kind, ok=not findings, findings=findings)
