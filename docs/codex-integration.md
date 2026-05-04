# Codex SDK integration

Prudentia owns the assignment workflow and exposes Codex through one narrow boundary: `src/prudentia/codex/adapter.py`.

## Adapter modes

- `OfflineCodexAdapter`: deterministic local generation for tests and demos. It requires no credentials.
- `LiveCodexAdapter`: readiness and bounded task execution for local Codex SDK/CLI when configured.

The live adapter checks only whether `codex_app_server` is importable or whether a `codex` executable is available. It does not read credentials. If live execution fails, it returns a structured failed task result with remediation guidance.

## Task contract

Each task receives:

- task kind
- prompt
- context manifest path
- allowed write globs
- expected artifacts
- read-only or workspace-write mode

Each task returns:

- result status
- task/thread IDs when available
- timestamps
- changed files
- unresolved issues
- human-readable summary

After a task finishes, Prudentia compares changed files with the task's allowed write globs. Any out-of-scope write fails the task result and records the offending paths in unresolved issues; Prudentia does not silently filter or bless those changes.

## Prompt control block

Every prompt starts with the Prudentia control block requiring the worker to operate only inside the workspace, use the context manifest as source of truth, avoid teacher-only leaks, and update `.prudentia/codex_status.json`.

## Project-scoped Codex settings

Workspace creation writes `.codex/config.toml` with conservative defaults:

- `approval_policy = "on-request"`
- `sandbox_mode = "workspace-write"`
- workspace-local writable roots
- network disabled
- prompt logging disabled
- history persistence disabled

Prudentia never modifies user-level Codex configuration.

## Live SDK risk

Codex SDK and CLI behavior can change independently of this MVP. The adapter is intentionally isolated so future updates can be made without changing generation, validation, reporting, export, CLI, or server code.
