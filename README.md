# Prudentia MVP

Prudentia is a local-first CS assignment workbench for teachers. The MVP creates a complete Python 3.12 + pytest assignment workspace, validates the reference solution through an explicit test-runner boundary, simulates weak/partial/misconception submissions, and packages separate student and teacher ZIP exports only after review approval, passing validation, and safety scanning.

The repository is intentionally small and production-shaped rather than speculative. There is no database, cloud service, LMS integration, auth system, queue, or multi-language plugin layer in the MVP.

## What the MVP includes

- Local CLI: `prudentia doctor`, `create`, `generate`, `validate`, `simulate`, `report`, `approve`, `export`, `status`, and `clean-runs`.
- Local FastAPI server and browser workbench launched by `prudentia ui`.
- Workspace boundary that writes `prudentia.yaml`, `.codex/config.toml`, `.prudentia/` state, assignment folders, reports, and exports.
- Codex boundary with deterministic offline generation and a live adapter isolated in `src/prudentia/codex/adapter.py`.
- Context manifest boundary for task-scoped included files, roles, write globs, and privacy warnings.
- Validation boundary for required files and artifact consistency.
- Test-runner boundary that prefers Docker, mounts the ephemeral Docker workspace copy read-only, and requires `--allow-native-execution` for host pytest execution.
- Generate All orchestration for generation, validation, bounded repair, simulation, and report refresh.
- Simulation, reporting, and approval-gated export boundaries with manifests and safety scanner results.
- Current-workspace marker so CLI/UI commands run from the parent directory can reopen the latest created workspace.

## Requirements

- Python 3.12 or newer.
- Docker for default sandboxed validation.
- Optional local Codex installation and authentication handled outside Prudentia.

## Install

From the repository root:

```bash
python -m pip install -e .
```

For development on a clean machine, installing the project is enough because the MVP uses conservative Python dependencies listed in `pyproject.toml`.

## Gate

```bash
python -m pip install -e ".[dev]"
make gate
```

`make gate` runs Ruff linting, Ruff format check, pytest, package build, and package metadata validation. The frontend is static HTML/CSS/JavaScript served from package data, so there is no separate Node build.

## Docker setup for default sandbox runs

The Docker runner expects an image with Python, pytest, and pytest-json-report already installed because the runtime container is launched with network disabled.

```bash
docker build -f docker/prudentia-pytest.Dockerfile -t prudentia-pytest:3.12 .
```

`prudentia doctor` reports both Docker daemon readiness and whether the expected Docker image is present.

Default validation uses Docker:

```bash
prudentia validate
```

Native execution is an explicit escape hatch and still runs on an ephemeral copy, not the source workspace:

```bash
prudentia validate --allow-native-execution
prudentia simulate --profiles weak,partial,misconception --allow-native-execution
```

`prudentia generate --all` also runs validation, simulation, and report refresh. Add `--allow-native-execution` only when Docker is unavailable and you accept host execution risk.

## Codex setup

Prudentia never asks for OpenAI API keys, ChatGPT credentials, session cookies, OAuth tokens, or local auth files. To use live Codex, install and authenticate Codex locally using the Codex-supported flow outside Prudentia, then run:

```bash
prudentia doctor
prudentia generate --brief --use-codex
```

If Codex is unavailable, the deterministic offline adapter remains available for tests and demos. The live SDK/CLI logic is isolated in one module so SDK changes do not leak into workspace, validation, export, or UI code.

## CLI demo

```bash
prudentia doctor
prudentia create --title "Palindrome checker" --course CS101 --topic "strings and functions" --difficulty beginner
cd palindrome-checker
prudentia generate --all --allow-native-execution
prudentia validate --allow-native-execution
prudentia simulate --profiles weak,partial,misconception --allow-native-execution
prudentia report
prudentia approve --all
prudentia export student
prudentia export teacher
prudentia status
```

Expected outputs:

- `exports/student/palindrome-checker-student.zip`
- `exports/teacher/palindrome-checker-teacher.zip`
- `reports/validation_report.json`
- `reports/teacher_report.md`
- `reports/simulation_matrix.md`

Exports are blocked until `brief`, `starter`, `solution`, `tests`, and `rubric` are approved and validation has passed. The student ZIP contains only:

- `brief.md`
- `README.student.md`
- `pyproject.toml`
- `starter/**`
- `tests/visible/**`

The teacher ZIP contains teaching artifacts and excludes `.codex/**`, export folders, Prudentia action logs, context manifests, and credential-like content.

## UI launch

```bash
prudentia ui --port 4898
```

Open `http://127.0.0.1:4898` in a browser. The UI is a guided workbench with workspace create/open, doctor, Generate All and individual generation buttons, context preview, artifact tabs, validation, simulation, report refresh, and export controls.

## Workspace shape

A created workspace uses the documented MVP schema:

```text
<assignment-slug>/
  prudentia.yaml
  brief.md
  README.student.md
  rubric.md
  pyproject.toml
  starter/src/assignment.py
  solution/src/assignment.py
  tests/visible/test_basic.py
  tests/hidden/test_edge_cases.py
  simulations/{weak,partial,misconception}/src/assignment.py
  reports/{validation_report.json,teacher_report.md,simulation_matrix.md}
  exports/{student,teacher}/
  .codex/config.toml
  .prudentia/
```

The workspace folder is the source of truth. All writes use normalized paths and reject traversal outside the workspace root.

## Example assignment

`examples/palindrome-checker/` contains the deterministic MVP assignment artifacts without run records or export ZIPs.

## Design notes

See:

- `docs/architecture.md`
- `docs/data-privacy.md`
- `docs/sandboxing.md`
- `docs/codex-integration.md`
