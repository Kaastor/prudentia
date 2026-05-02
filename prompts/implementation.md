# Prudentia MVP Staff Implementation Prompt

You are a staff-level implementation agent. Build the full Prudentia MVP as a production-shaped, local-first repository, then return the complete repository as a ZIP archive.

## Source Of Truth

Use `docs/requirements.md` as the canonical product and requirements specification. Use `README.md` as product philosophy and tone context. If a detail is missing, choose the smallest durable implementation that satisfies the MVP behavior without expanding scope.

Do not replace the requirements with a different architecture. Implement the documented MVP:

- Local TypeScript/Node backend.
- React + Vite local web UI.
- Thin CLI for direct validation of system functions.
- Local workspace folder as source of truth.
- Python 3.12 + pytest assignment generation and validation.
- Codex integration behind a clear adapter boundary.
- Docker-based test runner contract with a native execution escape hatch.
- Student and teacher ZIP exports with safety scanning.
- Minimal automated tests that prove the core behaviors work.

## Staff Implementation Standard

Treat "staff-level" as a quality bar, not a complexity bar.

Build the smallest complete MVP that is durable:

- Clear module ownership and narrow responsibilities.
- Honest interfaces around durable boundaries: filesystem, Codex, test execution, HTTP, CLI, export packaging.
- Explicit data contracts with runtime validation where inputs come from files, CLI args, HTTP, or generated artifacts.
- Boring, readable TypeScript over clever abstractions.
- Small cohesive functions with names that explain intent.
- Minimal duplication is acceptable until there is a real repeated pattern.
- No speculative plugin systems, factories, background queues, databases, auth systems, cloud sync, LMS integrations, or language adapters beyond Python/pytest.
- No placeholder-only implementation for MVP-critical behavior.
- No single-file monolith.
- No broad public APIs beyond what the CLI, local server, and packages need now.

Every changed or generated file must support the MVP, tests, packaging, docs, or required local developer workflow.

## Required Repository Shape

Create a complete monorepo with this shape unless there is a strong implementation reason to make a smaller equivalent boundary:

```text
prudentia/
  apps/
    cli/
    web/
    local-server/
  packages/
    core/
    workspace/
    codex-adapter/
    validators/
    runner-docker/
    generators/
    exporters/
    reporting/
    templates-python-pytest/
  examples/
    palindrome-python-pytest/
  docs/
  tests/
  package.json
  pnpm-workspace.yaml
  tsconfig.base.json
  README.md
  SECURITY.md
  LICENSE
```

Prefer `pnpm`, Node.js 20+, TypeScript, Vitest, Fastify, Commander, React, Vite, Zod, and a maintained ZIP library. Keep dependency choices conservative and justified by current needs.

## Required Core Behaviors

Implement enough of each behavior for the MVP to work end-to-end from the CLI and local UI.

### Workspace Management

Implement workspace creation that writes:

- `prudentia.yaml`
- `.codex/config.toml`
- `.prudentia/workflow_state.json`
- `.prudentia/action_log.jsonl`
- `.prudentia/context_manifests/`
- `.prudentia/runs/`
- `.prudentia/checkpoints/`
- `.prudentia/export_manifests/`
- deterministic assignment folders: `starter/`, `solution/`, `tests/visible/`, `tests/hidden/`, `simulations/`, `reports/`, `exports/`

Validate paths so all writes remain inside the workspace root. Reject path traversal.

### Codex Adapter

Create a `CodexAdapter` interface matching the requirements. Keep real Codex SDK usage isolated in `packages/codex-adapter`.

The MVP must be testable without live Codex credentials. Provide a deterministic local implementation for tests and offline demo generation, and a real adapter boundary that can be wired to `@openai/codex-sdk` when available. Do not inspect, copy, parse, export, or request `~/.codex/auth.json` or ChatGPT credentials.

If the exact SDK API cannot be verified in the implementation environment, keep the adapter API stable, make readiness fail gracefully with actionable setup guidance, and keep all non-Codex system behavior fully functional and tested.

### Generation Pipeline

Implement `generate --all` and individual generation steps:

- brief
- starter
- solution
- tests
- rubric
- simulations
- report

For the deterministic MVP path, generate a coherent Python/pytest assignment such as "Palindrome checker". The generated assignment must include:

- `brief.md`
- `README.student.md`
- `starter/src/assignment.py`
- `solution/src/assignment.py`
- `tests/visible/test_basic.py`
- `tests/hidden/test_edge_cases.py`
- `rubric.md`
- simulated weak, partial, and misconception submissions

Starter code must not include the complete reference solution. Solution code must pass visible and hidden tests.

### Validation

Implement deterministic validation of required files and artifact structure. Run pytest through the Docker runner by default, with a native execution escape hatch only when explicitly requested by CLI flag or advanced UI setting.

Record validation output in:

- `reports/validation_report.json`
- `.prudentia/runs/<run-id>/`

The test runner must operate on an ephemeral run copy, not directly on the source workspace.

### Export Packaging

Implement student and teacher ZIP exports.

Student export includes only:

- `brief.md`
- `README.student.md`
- `pyproject.toml`
- `starter/**`
- `tests/visible/**`

Student export must block:

- `solution/**`
- `tests/hidden/**`
- `simulations/**`
- `reports/**`
- `exports/**`
- `.prudentia/**`
- `.codex/**`
- obvious solution leak content such as `REFERENCE SOLUTION`, `hidden test`, or paths to solution files

Teacher export includes teaching artifacts but must block credentials, `.codex/**`, action logs, context manifests, tokens, `OPENAI_API_KEY`, `sk-`, session markers, and OS temp files.

Every export writes an export manifest under `.prudentia/export_manifests/`.

### Reports

Generate:

- `reports/teacher_report.md`
- `reports/simulation_matrix.md`

Reports should summarize validation status, generated artifacts, simulation outcomes, unresolved issues, and export status.

### Local HTTP Server

Implement the local Fastify server endpoints from `docs/requirements.md`:

- `GET /api/health`
- `POST /api/workspaces`
- `GET /api/workspaces/:id`
- `POST /api/workspaces/:id/generate`
- `POST /api/workspaces/:id/validate`
- `POST /api/workspaces/:id/simulate`
- `POST /api/workspaces/:id/report`
- `POST /api/workspaces/:id/export`
- `GET /api/workflows/:runId/events`

Use simple local state. Do not introduce a database.

### Local Web UI

Implement a guided workbench, not a chat interface. It must support:

- workspace create/open
- doctor/readiness display
- Generate All and individual generation buttons
- context preview
- artifact review tabs
- validation result display
- simulation matrix display
- student and teacher export controls
- clear status and error states

Keep the UI utilitarian and suited to a local teacher tool. Avoid marketing-page layout.

### Thin CLI

Implement a thin CLI that exercises the real system functions so a coding agent can validate the MVP without using the UI:

```bash
prudentia doctor
prudentia ui [--port 4898]
prudentia create --title "Palindrome checker" --course CS101 --topic "strings and functions" --difficulty beginner
prudentia generate --all
prudentia generate --brief
prudentia generate --starter
prudentia generate --solution
prudentia generate --tests
prudentia generate --rubric
prudentia validate [--allow-native-execution]
prudentia simulate --profiles weak,partial,misconception
prudentia report
prudentia export student
prudentia export teacher
prudentia status
prudentia clean-runs
```

The CLI should be thin orchestration over package APIs, not duplicate business logic.

## Minimum Test Suite

Add a focused automated test suite. It does not need exhaustive UI coverage, but it must validate the core system behaviors:

- workspace creation writes required folders, `prudentia.yaml`, `.codex/config.toml`, and initial state
- schemas reject invalid workspace metadata
- generation creates required assignment artifacts
- starter code does not contain complete solution markers
- validator detects missing required files
- reference solution passes generated pytest tests in native test mode for CI portability
- simulation matrix is written
- student export excludes solution, hidden tests, reports, `.prudentia`, and `.codex`
- student export blocks forbidden content leaks
- teacher export blocks credential-like content
- CLI smoke path can create, generate, validate, report, and export in a temporary workspace

Provide these commands and make them pass:

```bash
pnpm install
pnpm build
pnpm test
pnpm lint
pnpm prudentia doctor
pnpm prudentia create --title "Palindrome checker" --course CS101 --topic "strings and functions" --difficulty beginner
pnpm prudentia generate --all
pnpm prudentia validate --allow-native-execution
pnpm prudentia simulate --profiles weak,partial,misconception
pnpm prudentia report
pnpm prudentia export student
pnpm prudentia export teacher
```

If Docker is unavailable during tests, tests may use the native execution escape hatch, but production defaults must still prefer Docker.

## Documentation

Include practical docs:

- README with install, Codex setup, Docker setup, CLI demo, UI launch, and test instructions.
- SECURITY.md documenting local execution risks, credential boundaries, export scanner guarantees, and issue reporting.
- Short docs for architecture, data privacy, sandboxing, and Codex SDK integration.

Do not ask users for OpenAI API keys or ChatGPT credentials in the UI. Codex setup docs must direct users to local Codex authentication outside Prudentia.

## Implementation Order

Work in this order and keep each step shippable:

1. Monorepo scaffolding, package scripts, TypeScript config.
2. Core types and schemas.
3. Workspace creation and filesystem safety.
4. Deterministic generator and prompt/context manifest contracts.
5. Artifact validators.
6. Runner abstraction with Docker default and native escape hatch.
7. Reporting.
8. Export scanner and packager.
9. CLI commands over package APIs.
10. Local server endpoints.
11. React workbench.
12. Minimal tests and example assignment.
13. Documentation and final ZIP packaging.

## Completion Criteria

Before returning the ZIP:

- Build passes.
- Tests pass.
- Lint passes or the README clearly explains why lint is not configured.
- CLI demo path works in a clean temporary workspace.
- Student ZIP does not contain solution files, hidden tests, reports, `.prudentia`, or `.codex`.
- Teacher ZIP does not contain credentials or `.codex`.
- No `node_modules`, build caches, run outputs, generated export ZIPs, credentials, or local machine paths are included in the final repository ZIP.
- No MVP-critical TODOs remain.

## Final Response Contract

Return:

1. A ZIP archive named `prudentia-mvp.zip` containing the full repository.
2. A short implementation summary.
3. The exact validation commands you ran and their results.
4. Any honest residual risks, especially around live Codex SDK behavior or Docker availability.

Do not return only snippets. Do not return pseudocode. Do not stop after a plan. The deliverable is the full repository ZIP.
