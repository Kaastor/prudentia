# Prudentia MVP Staff Implementation Prompt

You are a staff-level implementation agent. Build the full Prudentia MVP as a production-shaped, local-first repository, then return the complete repository as a ZIP archive.

## Source Of Truth

Use the attached Prudentia MVP requirements document as the canonical product and requirements specification. Use any attached README or product philosophy note as tone context. If a detail is missing, choose the smallest durable implementation that satisfies the MVP behavior without expanding scope.


Do not replace the requirements with a different architecture. Implement the documented MVP:

- Local service/runtime.
- Local browser-based web UI.
- Thin CLI for direct validation of system functions.
- Local workspace folder as source of truth.
- Python 3.12 + pytest assignment generation and validation.
- Codex integration behind a clear boundary.
- Sandboxed test-runner boundary with a native execution escape hatch.
- Student and teacher ZIP exports with safety scanning.
- Minimal automated tests that prove the core behaviors work.

## Staff Implementation Standard

Treat "staff-level" as a quality bar, not a complexity bar.

Build the smallest complete MVP that is durable:

- Clear module ownership and narrow responsibilities.
- Honest interfaces around durable boundaries: filesystem, Codex, test execution, HTTP, CLI, export packaging.
- Explicit data contracts with runtime validation where inputs come from files, CLI args, HTTP, or generated artifacts.
- Boring, readable typed code over clever abstractions.
- Small cohesive functions with names that explain intent.
- Minimal duplication is acceptable until there is a real repeated pattern.
- No speculative plugin systems, factories, background queues, databases, auth systems, cloud sync, LMS integrations, or language adapters beyond Python/pytest.
- No placeholder-only implementation for MVP-critical behavior.
- No single-file monolith.
- No broad public APIs beyond what the CLI, local server, and owned modules need now.

Every changed or generated file must support the MVP, tests, packaging, docs, or required local developer workflow.

## Required Ownership Boundaries

Create a complete repository with clear ownership boundaries. Exact directory names, package names, framework choices, and TypeScript shapes are implementation-owned, but the repo must keep these responsibilities separated:

| Component | Responsibilities |
| --- | --- |
| CLI | Starts UI/server, runs direct workflows, prints errors, supports automation. |
| Local web UI | Guided assignment creation, context preview, progress, review, approval, export. |
| Local server | Owns HTTP API, workflow orchestration, and progress events. |
| Workspace boundary | Creates folders, writes assignment metadata, checkpoints, manifests, and logs. |
| Codex boundary | Builds prompts, calls Codex SDK when available, tracks task IDs, records changed files. |
| Context manifest boundary | Determines files shown to teacher and included in Codex tasks. |
| Validation boundary | Checks required files, metadata, brief/test/rubric consistency, and forbidden files. |
| Test-runner boundary | Runs pytest in isolated execution path with network disabled by default. |
| Simulation boundary | Generates weak/partial/misconception submissions and runs tests. |
| Reporting boundary | Writes validation report, simulation matrix, and teacher report. |
| Export boundary | Creates student and teacher ZIPs with manifest and safety scan. |

Choose mature, boring libraries that fit the selected local runtime. The implementation must provide documented install, build, test, lint, and CLI demo commands. Keep dependency choices conservative and justified by current needs.

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

Create an explicit Codex integration boundary. The exact TypeScript interface is implementation-owned, but all real Codex SDK usage must stay inside one narrow owned module.

The boundary must support:

- readiness checks without reading credentials
- running one bounded task in one workspace
- task kinds for planning, brief generation, starter generation, solution generation, test generation, repair, rubric generation, simulation generation, and quality review
- prompt input
- context manifest path
- allowed write globs
- expected artifacts
- read-only vs workspace-write mode
- result status
- task/thread IDs when available
- timestamps
- changed files
- unresolved issues
- human-readable summary

The MVP must be testable without live Codex credentials. Provide a deterministic local implementation for tests and offline demo generation, and a real adapter boundary that can be wired to the official Codex SDK when available. Do not inspect, copy, parse, export, or request `~/.codex/auth.json` or ChatGPT credentials.

If the SDK API cannot be verified in the implementation environment, keep the boundary stable, make readiness fail gracefully with actionable setup guidance, and keep all non-Codex system behavior fully functional and tested.

When a workspace is created, write conservative project-scoped Codex settings if supported by the SDK/CLI. These settings must prefer workspace-write behavior, approval before risky actions, no network access by default, and writable roots limited to the assignment workspace.

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

Use stable prompt templates for AI-assisted tasks. Each prompt begins with this control block or a close equivalent:

```text
You are the Codex worker for Prudentia, a local-first CS assignment studio.
Operate only inside the current assignment workspace.
Use the context manifest as the source of truth for allowed files.
Do not read or write outside the assignment workspace.
Do not include teacher-only solution or hidden tests in student-facing files.
Prefer simple, teachable code over clever code.
After completing the task, update .prudentia/codex_status.json with:
  - task_kind
  - changed_files
  - assumptions
  - unresolved_issues
  - next_recommended_action
```

Create an explicit context manifest boundary. The exact TypeScript shape is implementation-owned, but the manifest must be a durable structured record that includes:

- schema version
- manifest ID
- workspace ID
- task kind
- creation timestamp
- included files with path, reason, and role
- roles for student-visible, teacher-only, metadata, test, and report files
- excluded globs
- allowed write globs
- privacy warnings

### Validation

Implement deterministic validation of required files and artifact structure. Run pytest through the Docker runner by default, with a native execution escape hatch only when explicitly requested by CLI flag or advanced UI setting.

Create an explicit test-runner boundary. The exact Docker command is implementation-owned, but the boundary must preserve these safety invariants:

- run generated code against an ephemeral workspace copy
- disable network access by default
- avoid source workspace writes
- write results only to the explicit run result directory
- capture stdout, stderr, exit code, pytest report, and run metadata
- support native pytest execution only through an explicit escape hatch

Record validation output in:

- `reports/validation_report.json`
- `.prudentia/runs/<run-id>/`

Use this run output boundary:

```text
.prudentia/runs/<run-id>/
  workspace-copy/
  stdout.txt
  stderr.txt
  exit_code.txt
  pytest_report.json
  run_metadata.json
```

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

### Local Server Boundary

Implement a local server boundary for the web UI and CLI orchestration. Exact framework and route names are implementation-owned, but the server must expose operations for:

- readiness/health
- workspace creation
- workspace metadata and artifact status lookup
- generation
- validation
- simulation
- report refresh
- student and teacher export
- workflow progress streaming or polling

Create an explicit workflow progress boundary. The exact event type is implementation-owned, but progress events must include:

- run ID
- workspace ID
- event kind for run start, Codex task start/finish, validation start/finish, export start/finish, and error
- human-readable message
- creation timestamp
- optional structured payload

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

The CLI should be thin orchestration over owned domain APIs, not duplicate business logic.

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

Provide the implementation's install, build, test, and lint commands, and make them pass. Also provide a CLI smoke path equivalent to:

```bash
<install command>
<build command>
<test command>
<lint command>
<prudentia command> doctor
<prudentia command> create --title "Palindrome checker" --course CS101 --topic "strings and functions" --difficulty beginner
<prudentia command> generate --all
<prudentia command> validate --allow-native-execution
<prudentia command> simulate --profiles weak,partial,misconception
<prudentia command> report
<prudentia command> export student
<prudentia command> export teacher
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

1. Repository scaffolding, ownership boundaries, and build scripts.
2. Core types and schemas.
3. Workspace creation and filesystem safety.
4. Deterministic generator and prompt/context manifest boundaries.
5. Artifact validators.
6. Test-runner boundary with Docker default and native escape hatch.
7. Reporting.
8. Export scanner and packager.
9. CLI commands over domain APIs.
10. Local server operations.
11. Web workbench.
12. Minimal tests and example assignment.
13. Documentation and final ZIP packaging.

Use these milestone exit criteria while working:

| Milestone | Deliverable | Exit criteria |
| --- | --- | --- |
| M1: Repo and schemas | Repository boundaries, core domain models, `prudentia.yaml` parser, workspace creation. | `prudentia create` produces valid folder and metadata. |
| M2: Codex boundary | Local Codex SDK integration boundary, readiness check, one task execution or graceful offline fallback. | Codex path can write `brief.md` when configured; deterministic fallback works in tests. |
| M3: Generation pipeline | Generate brief, starter, solution, tests, rubric. | Generate All creates required artifacts. |
| M4: Docker runner | Python/pytest sandbox runner and validation reports. | Reference solution can be tested in container when Docker is available. |
| M5: Simulation and repair | Simulated submissions and bounded repair loop. | Simulation matrix is generated. |
| M6: Export scanner | Student and teacher ZIP packages with manifests. | Forbidden-file and credential-leak tests pass. |
| M7: Local web UI | Guided UI for all MVP workflows. | Demo can be completed without CLI except app launch. |
| M8: Open-source polish | README, docs, tests, examples, SECURITY.md. | External developer can run demo from docs. |

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
