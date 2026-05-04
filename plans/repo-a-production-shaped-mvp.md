# Repo A Production-Shaped MVP Implementation Plan

## Summary

Use Repo A (`/home/przemek/Downloads/prudentia-mvp`) as the base, fix its MVP-critical gaps, and selectively borrow the best durable ideas from Repo B and Repo C without widening scope.

The goal is to make Repo A a production-shaped MVP foundation: local-first, deterministic, reviewable, sandboxed, export-safe, and teacher-gated. The work is not complete until the implementation is audited, tested, and independently agent-verified against the MVP requirements.

## Implementation Quality Bar

This plan must be executed with `docs/requirements.md` as the product source of truth and `prompts/implementation.md` as the implementation-quality bar. If details are missing, choose the smallest durable implementation that satisfies the MVP behavior without expanding scope.

- Treat staff-level implementation as a quality bar, not a complexity bar.
- Keep clear module ownership and narrow responsibilities.
- Keep honest interfaces around durable boundaries: filesystem, Codex, test execution, HTTP, CLI, export packaging, context manifests, validation, simulation, reporting, and workspace state.
- Use explicit data contracts with runtime validation for file inputs, CLI args, HTTP payloads, and generated artifacts.
- Prefer boring, readable typed code, small cohesive functions, and conservative dependencies.
- Do not add speculative plugin systems, factories, queues, databases, auth systems, cloud sync, LMS integrations, or non-Python language adapters.
- Do not leave placeholder-only behavior for MVP-critical workflows.
- Keep the CLI thin over owned domain APIs; do not duplicate business logic between CLI, server, and UI.
- Keep the UI a guided local teacher workbench, not a chat interface or marketing page.
- Every changed file must support the MVP, tests, packaging, docs, or required local developer workflow.

## Required Boundary Invariants

- Workspace writes stay inside the workspace root and reject path traversal.
- Codex usage stays behind one narrow adapter boundary, works without live credentials through deterministic fallback, never inspects `~/.codex/auth.json`, and records task kind, context manifest, allowed writes, changed files, unresolved issues, and summary.
- Context manifests are durable structured records with included files, roles, excluded globs, allowed write globs, and privacy warnings.
- Test execution uses an ephemeral workspace copy, disables network by default, avoids source workspace writes, captures stdout/stderr/exit code/pytest report/run metadata, and allows native pytest only through explicit escape hatch.
- Student exports include only brief, student README, pyproject, starter code, and visible tests; they must block solution, hidden tests, simulations, reports, exports, `.prudentia`, `.codex`, and obvious solution leaks.
- Teacher exports include teaching artifacts but block credentials, `.codex`, action logs, context manifests, tokens, `OPENAI_API_KEY`, `sk-`, session markers, and temp files.
- Reports summarize validation status, artifacts, simulation outcomes, unresolved issues, and export status.

## Key Changes

- Approval-gated export:
  - Block student and teacher exports unless core artifacts are `approved` and validation is `passed`.
  - Keep export scanner and ZIP allowlists unchanged after the gate passes.
  - Record blocked export manifests and clear progress errors.

- Full Generate All workflow:
  - Make `generate_all` orchestrate generation, validation, up to two repair attempts, simulation, and report refresh.
  - Keep individual generation commands narrow.
  - Add CLI `--allow-native-execution` only for explicit local/dev use; Docker remains default.

- Bounded repair loop:
  - Run at most two `repair` Codex tasks after failed validation.
  - Revalidate after each repair.
  - Log each attempt and expose final validation status in the generation result.

- Codex write enforcement:
  - Fail any Codex task that changes files outside its allowed write globs.
  - Include offending paths in unresolved issues and progress logs.
  - Do not silently filter out out-of-scope writes.

- Borrow from Repo B:
  - Add an active/current workspace marker so CLI/UI can reliably reopen the latest workspace from the parent directory.
  - Strengthen Docker run isolation by adopting Repo B's read-only mounted workspace-copy pattern where compatible with Repo A's runner.
  - Split broad tests into clearer focused test files if this stays low-churn.

- Borrow from Repo C:
  - Add doctor/readiness reporting for missing Docker images before validation fails.
  - Keep or add strict model validation where Repo A already uses Pydantic.
  - Add `ruff` only if it can be introduced without fighting existing lint style; otherwise keep Repo A's current lint script.

- Documentation and polish from the implementation prompt:
  - Add or update README instructions for install, Codex setup, Docker setup, CLI demo, UI launch, tests, and lint.
  - Add or update `SECURITY.md` for local execution risks, credential boundaries, export scanner guarantees, and issue reporting.
  - Add short architecture/privacy/sandboxing/Codex notes only where missing and useful.

## Public Interfaces

- `generate_all(root, *, use_live_codex=False, allow_native_execution=False, prefer_docker=True, max_repair_attempts=2)` becomes the high-level full workflow entrypoint.
- CLI `prudentia generate --all` gains explicit native execution support.
- Export behavior intentionally changes: exports require approval and passing validation.
- Workspace discovery improves through a current-workspace marker, without removing explicit `--workspace`.

## Test Plan

- Approval-blocked export before approval.
- Export succeeds after approval plus passing validation.
- Generate All runs validation, simulation, and report refresh.
- Repair loop stops after two attempts and stops early on success.
- Codex write-boundary violations fail the task.
- Current-workspace marker resolves the latest created workspace.
- Docker image readiness appears in doctor output.
- Run full verification:
  - `python -m pytest -q`
  - `python scripts/check_build.py`
  - `python scripts/lint.py`
- Run or document the CLI smoke path in a clean temporary workspace:
  - `prudentia doctor`
  - `prudentia create --title "Palindrome checker" --course CS101 --topic "strings and functions" --difficulty beginner`
  - `prudentia generate --all`
  - `prudentia validate --allow-native-execution`
  - `prudentia simulate --profiles weak,partial,misconception`
  - `prudentia report`
  - approve required artifacts
  - `prudentia export student`
  - `prudentia export teacher`
  - `prudentia status`

## Acceptance Gates

- Production-shaped: code keeps clear ownership boundaries, avoids speculative architecture, and preserves local-first MVP behavior.
- Audited: security-sensitive paths are reviewed manually, including path safety, Codex write limits, sandbox execution, export allowlists, credential scanning, action logs, and context manifests.
- Tested: focused regression tests and the repo's full verification commands pass.
- Agent-verified: after implementation, a separate review pass checks the result against `docs/requirements.md`, this plan, and the previous three-repo review findings.
- Evidence-backed: final handoff includes changed behavior, files touched, commands run, test results, and any residual risks.
- No MVP-critical TODOs remain, and no credentials, generated export ZIPs, run outputs, build caches, or local machine paths are included in any final handoff artifact.

## Assumptions

- Repo A remains the implementation base.
- Borrowed B/C ideas are implemented only where they improve MVP durability without importing unrelated architecture.
- No dangerous export override is added.
- Approval remains manual; Generate All does not auto-approve artifacts.
- Docker remains the production default; native execution is only available through explicit flags for local/dev/test workflows.
