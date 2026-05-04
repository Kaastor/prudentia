# Architecture

Prudentia MVP is a local-first Python repository with a thin CLI, a local FastAPI server, static web workbench, and filesystem-backed workspace state.

## Ownership boundaries

| Boundary | Module | Responsibility |
| --- | --- | --- |
| CLI | `src/prudentia/cli.py` | Parse commands, print results, call domain services. |
| Server | `src/prudentia/server/app.py` | Local HTTP API and UI orchestration. |
| Web UI | `src/prudentia/web/` | Guided workbench controls and polling. |
| Workspace | `src/prudentia/workspace/manager.py` | Create folders, read/write metadata, action logs, workflow state, checkpoints, current-workspace marker. |
| Core contracts | `src/prudentia/core/` | Pydantic models, path safety, JSON IO, progress events, doctor checks. |
| Codex | `src/prudentia/codex/` | Context manifests, prompts, offline adapter, live SDK/CLI adapter. |
| Generation | `src/prudentia/generation/` | Deterministic assignment artifacts and generation pipeline. |
| Validation | `src/prudentia/validation/` | Required-file checks, content checks, validation report orchestration. |
| Runner | `src/prudentia/runner/` | Pytest execution on ephemeral workspace copies. |
| Simulation | `src/prudentia/simulation/` | Fake weak/partial/misconception submissions and matrix generation. |
| Reporting | `src/prudentia/reporting/` | Teacher report refresh. |
| Export | `src/prudentia/export/` | Scanner, ZIP packager, export manifests. |

## Data flow

1. `create_workspace` writes the deterministic folder shape, `prudentia.yaml`, project-scoped Codex settings, workflow state, and action log.
2. `generate_all` checkpoints the workspace, creates context manifests, builds prompts, calls either the deterministic adapter or the live Codex adapter, validates, runs up to two repair tasks after failed validation, simulates generated submissions, and refreshes the teacher report.
3. `validate_workspace` checks artifacts and runs the reference solution through the runner boundary.
4. `simulate_profiles` writes fake submissions and runs the same tests against each profile.
5. `refresh_reports` summarizes validation, artifacts, simulations, issues, and export status.
6. `package_export` checks approval and validation readiness, selects files, scans paths and contents, writes the ZIP, and records an export manifest. Blocked exports also write manifests.

## State model

The workspace folder is the only source of truth. There is no database. Server progress is persisted in `.prudentia/workflow_state.json` and action events are appended to `.prudentia/action_log.jsonl`.

When a workspace is created or opened, the parent directory gets `.prudentia-current-workspace.json`. Commands run from the parent can use that marker to reopen the latest workspace without a database or global config.

## Runtime validation

Inputs from YAML, JSON, CLI, and HTTP are validated using Pydantic models or explicit path checks. Filesystem writes call `safe_join` to reject absolute paths and traversal outside the workspace root.
