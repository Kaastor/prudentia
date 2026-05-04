from __future__ import annotations

import hashlib
import importlib.util
import os
import shutil
import subprocess
from pathlib import Path
from typing import Literal, Protocol
from uuid import uuid4

from pydantic import BaseModel, Field

from prudentia.codex.prompts import CONTROL_BLOCK
from prudentia.core.jsonio import write_json
from prudentia.core.models import TaskKind
from prudentia.core.paths import iter_files, matches_any, relative_to_root, safe_join
from prudentia.core.time import utc_now_iso
from prudentia.workspace.manager import Workspace, log_action

CodexMode = Literal["read_only", "workspace_write"]
CodexStatus = Literal["succeeded", "failed", "skipped"]


class CodexReadiness(BaseModel):
    available: bool
    mode: str
    detail: str
    setup_guidance: str


class CodexTaskRequest(BaseModel):
    task_kind: TaskKind
    prompt: str = Field(min_length=1)
    context_manifest_path: str
    allowed_write_globs: list[str]
    expected_artifacts: list[str]
    mode: CodexMode = "workspace_write"


class CodexTaskResult(BaseModel):
    task_kind: TaskKind
    status: CodexStatus
    task_id: str | None = None
    thread_id: str | None = None
    started_at: str
    finished_at: str
    changed_files: list[str] = Field(default_factory=list)
    unresolved_issues: list[str] = Field(default_factory=list)
    summary: str


class CodexAdapter(Protocol):
    def readiness(self) -> CodexReadiness: ...

    def run_task(self, workspace: Workspace, request: CodexTaskRequest) -> CodexTaskResult: ...


def file_snapshot(root: Path) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for path in iter_files(root, exclude_globs=[".prudentia/action_log.jsonl", "exports/**"]):
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            continue
        snapshot[relative_to_root(root, path)] = digest
    return snapshot


def changed_files(before: dict[str, str], after: dict[str, str]) -> list[str]:
    changed: list[str] = []
    for rel, digest in after.items():
        if before.get(rel) != digest:
            changed.append(rel)
    for rel in before:
        if rel not in after:
            changed.append(rel)
    return sorted(changed)


def enforce_allowed_writes(request: CodexTaskRequest, result: CodexTaskResult) -> CodexTaskResult:
    offending = [path for path in result.changed_files if not matches_any(path, request.allowed_write_globs)]
    if not offending:
        return result
    issue = "Codex task changed files outside allowed write globs: " + ", ".join(offending)
    result.status = "failed"
    result.unresolved_issues = [*result.unresolved_issues, issue]
    result.summary = f"{result.summary} Write boundary violation: {', '.join(offending)}"
    return result


def enforce_expected_artifacts(root: Path, request: CodexTaskRequest, result: CodexTaskResult) -> CodexTaskResult:
    if result.status != "succeeded":
        return result
    missing = [path for path in request.expected_artifacts if not safe_join(root, path).exists()]
    if not missing:
        return result
    issue = "Codex task did not produce expected artifacts: " + ", ".join(missing)
    result.status = "failed"
    result.unresolved_issues = [*result.unresolved_issues, issue]
    result.summary = f"{result.summary} Missing expected artifacts: {', '.join(missing)}"
    return result


class OfflineCodexAdapter:
    """Deterministic implementation used for tests and offline demos."""

    def readiness(self) -> CodexReadiness:
        return CodexReadiness(
            available=True,
            mode="offline-deterministic",
            detail="Using deterministic local generation; no Codex credentials are required.",
            setup_guidance="Install and authenticate Codex locally to enable live AI-assisted tasks.",
        )

    def run_task(self, workspace: Workspace, request: CodexTaskRequest) -> CodexTaskResult:
        started = utc_now_iso()
        before = file_snapshot(workspace.root)
        from prudentia.generation.deterministic import write_deterministic_task

        generated = write_deterministic_task(workspace, request.task_kind)
        status_path = safe_join(workspace.root, ".prudentia/codex_status.json")
        write_json(
            status_path,
            {
                "task_kind": request.task_kind.value,
                "changed_files": generated,
                "assumptions": ["Deterministic Palindrome checker MVP path was used."],
                "unresolved_issues": [],
                "next_recommended_action": "Run validation and review artifacts.",
            },
        )
        after = file_snapshot(workspace.root)
        result = CodexTaskResult(
            task_kind=request.task_kind,
            status="succeeded",
            task_id=f"offline-{uuid4().hex[:12]}",
            thread_id=None,
            started_at=started,
            finished_at=utc_now_iso(),
            changed_files=changed_files(before, after),
            unresolved_issues=[],
            summary=f"Deterministically generated {request.task_kind.value} artifacts.",
        )
        result = enforce_allowed_writes(request, result)
        result = enforce_expected_artifacts(workspace.root, request, result)
        log_action(workspace.root, "codex_offline_task_finished", result.model_dump(mode="json"))
        return result


class LiveCodexAdapter:
    """Narrow boundary for live Codex SDK/CLI usage.

    Prudentia does not read credentials. Readiness checks only inspect whether a local
    Codex integration point is importable or executable. The Python SDK path is
    experimental upstream, so failures are surfaced as actionable task results.
    """

    def readiness(self) -> CodexReadiness:
        sdk_available = importlib.util.find_spec("codex_app_server") is not None
        codex_bin = shutil.which("codex")
        if sdk_available:
            return CodexReadiness(
                available=True,
                mode="python-sdk",
                detail="codex_app_server is importable. Prudentia can attempt a bounded local Codex task.",
                setup_guidance="Authenticate Codex locally outside Prudentia, then rerun the task.",
            )
        if codex_bin:
            try:
                completed = subprocess.run([codex_bin, "--version"], capture_output=True, text=True, timeout=10, check=False)
                version_detail = completed.stdout.strip() or completed.stderr.strip() or "codex command found"
            except (OSError, subprocess.TimeoutExpired) as exc:
                version_detail = f"codex command found but version check failed: {exc}"
            return CodexReadiness(
                available=True,
                mode="cli",
                detail=version_detail,
                setup_guidance="Authenticate Codex locally outside Prudentia. Python SDK support is preferred when available.",
            )
        return CodexReadiness(
            available=False,
            mode="unavailable",
            detail="No local Codex SDK import or codex executable was found.",
            setup_guidance="Install the Codex CLI or SDK and complete local Codex authentication outside Prudentia.",
        )

    def run_task(self, workspace: Workspace, request: CodexTaskRequest) -> CodexTaskResult:
        started = utc_now_iso()
        before = file_snapshot(workspace.root)
        readiness = self.readiness()
        if not readiness.available:
            return CodexTaskResult(
                task_kind=request.task_kind,
                status="failed",
                started_at=started,
                finished_at=utc_now_iso(),
                changed_files=[],
                unresolved_issues=[readiness.setup_guidance],
                summary=readiness.detail,
            )
        if readiness.mode == "python-sdk":
            return self._run_python_sdk_task(workspace, request, started, before)
        return self._run_cli_task(workspace, request, started, before)

    def _run_python_sdk_task(
        self,
        workspace: Workspace,
        request: CodexTaskRequest,
        started: str,
        before: dict[str, str],
    ) -> CodexTaskResult:
        try:
            from codex_app_server import Codex  # type: ignore[import-not-found]

            prompt = self._bounded_prompt(request)
            with Codex() as codex:
                thread = codex.thread_start()
                result = thread.run(prompt)
                final_response = getattr(result, "final_response", str(result))
                thread_id = getattr(thread, "id", None)
        except Exception as exc:  # pragma: no cover - depends on local Codex installation.
            return CodexTaskResult(
                task_kind=request.task_kind,
                status="failed",
                started_at=started,
                finished_at=utc_now_iso(),
                changed_files=[],
                unresolved_issues=["Live Codex SDK task failed; use deterministic mode or check local Codex setup."],
                summary=str(exc),
            )
        after = file_snapshot(workspace.root)
        result = CodexTaskResult(
            task_kind=request.task_kind,
            status="succeeded",
            task_id=f"sdk-{uuid4().hex[:12]}",
            thread_id=str(thread_id) if thread_id else None,
            started_at=started,
            finished_at=utc_now_iso(),
            changed_files=changed_files(before, after),
            unresolved_issues=[],
            summary=final_response[:1000],
        )
        result = enforce_allowed_writes(request, result)
        result = enforce_expected_artifacts(workspace.root, request, result)
        log_action(workspace.root, "codex_sdk_task_finished", result.model_dump(mode="json"))
        return result

    def _run_cli_task(
        self,
        workspace: Workspace,
        request: CodexTaskRequest,
        started: str,
        before: dict[str, str],
    ) -> CodexTaskResult:
        codex_bin = shutil.which("codex")
        if not codex_bin:
            return CodexTaskResult(
                task_kind=request.task_kind,
                status="failed",
                started_at=started,
                finished_at=utc_now_iso(),
                changed_files=[],
                unresolved_issues=["codex executable is not available."],
                summary="Install Codex or use deterministic mode.",
            )
        command = [
            codex_bin,
            "exec",
            "--cd",
            str(workspace.root),
            "--skip-git-repo-check",
            "--ephemeral",
            "--sandbox",
            "workspace-write",
            self._bounded_prompt(request),
        ]
        try:
            completed = subprocess.run(
                command,
                cwd=workspace.root,
                capture_output=True,
                text=True,
                timeout=int(os.environ.get("PRUDENTIA_CODEX_TIMEOUT_SECONDS", "600")),
                check=False,
            )
        except Exception as exc:  # pragma: no cover - depends on local Codex installation.
            return CodexTaskResult(
                task_kind=request.task_kind,
                status="failed",
                started_at=started,
                finished_at=utc_now_iso(),
                changed_files=[],
                unresolved_issues=["Live Codex CLI invocation failed."],
                summary=str(exc),
            )
        after = file_snapshot(workspace.root)
        status = "succeeded" if completed.returncode == 0 else "failed"
        summary = (completed.stdout.strip() or completed.stderr.strip() or f"codex exited with {completed.returncode}")[:1000]
        result = CodexTaskResult(
            task_kind=request.task_kind,
            status=status,
            task_id=f"cli-{uuid4().hex[:12]}",
            started_at=started,
            finished_at=utc_now_iso(),
            changed_files=changed_files(before, after),
            unresolved_issues=[] if status == "succeeded" else ["Codex CLI returned a non-zero exit code."],
            summary=summary,
        )
        result = enforce_allowed_writes(request, result)
        result = enforce_expected_artifacts(workspace.root, request, result)
        log_action(workspace.root, "codex_cli_task_finished", result.model_dump(mode="json"))
        return result

    @staticmethod
    def _bounded_prompt(request: CodexTaskRequest) -> str:
        if CONTROL_BLOCK not in request.prompt:
            return CONTROL_BLOCK + "\n" + request.prompt
        return request.prompt


def select_codex_adapter(use_live_codex: bool = False) -> CodexAdapter:
    return LiveCodexAdapter() if use_live_codex else OfflineCodexAdapter()
