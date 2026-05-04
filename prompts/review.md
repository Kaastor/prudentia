# Prudentia Three-Implementation Review Prompt

You are a staff-level software reviewer. Compare three independent repositories that implement `docs/requirements.md` for Prudentia.

Your goal is to determine which implementation is the best production foundation: the one that most faithfully satisfies the requirements, has the strongest production-shaped code, and uses the cleanest design, approach, and architecture.

## Inputs

Use these local repository paths:

```text
REPO_A=/home/przemek/Downloads/prudentia-mvp
REPO_B=/home/przemek/Downloads/prudentia-mvp (1)/prudentia-mvp-1
REPO_C=/home/przemek/Downloads/prudentia-mvp (2)/prudentia-mvp-2
REQUIREMENTS=/home/przemek/Nauka/prudentia/docs/requirements.md
IMPLEMENTATION_PROMPT=/home/przemek/Nauka/prudentia/prompts/implementation.md
```

If paths are not provided, ask for them before reviewing.

## Source Of Truth

Treat `docs/requirements.md` as the canonical product specification.

Use `prompts/implementation.md` only as implementation-quality context. Do not let a repository win by implementing a different product, expanding scope, or polishing around missing MVP behavior.

The MVP is a local-first CS assignment workbench for teachers. The core requirement is not a pretty UI or a generic AI wrapper. The core requirement is a deterministic, reviewable assignment production system with:

- local CLI and web UI workflows
- portable assignment workspace schema
- bounded Codex integration
- context preview
- generation, validation, simulation, reporting, and export
- Docker-first sandboxed pytest execution
- teacher approval gates
- strong export safety for student and teacher packages
- local audit trail
- production-shaped code with clear boundaries

## Review Principles

Inspect the code. README claims are not evidence.

Do not reward placeholder behavior, mock-only implementations, or happy-path demos that bypass required safety boundaries.

Prefer the smallest durable implementation that satisfies the MVP over broad architecture, plugin systems, queues, databases, auth layers, cloud services, or language adapters that the requirements explicitly do not need.

Judge production shape as a quality bar, not a complexity bar:

- clear module ownership
- narrow interfaces around real boundaries
- explicit runtime validation for file, CLI, HTTP, and generated-artifact inputs
- path traversal protection
- deterministic workspace and export behavior
- bounded repair loops
- actionable errors
- tests that protect core behavior
- readable, boring code
- no MVP-critical TODOs
- no credential handling or unsafe export leaks

## Required Review Workflow

For each repository:

1. Read the repository README, package manifests, docs, and source tree.
2. Identify the stack, entry points, install command, build command, test command, lint command, and CLI command shape.
3. Map the architecture against the required ownership boundaries:
   - CLI
   - local web UI
   - local server
   - workspace boundary
   - Codex boundary
   - context manifest boundary
   - validation boundary
   - test-runner boundary
   - simulation boundary
   - reporting boundary
   - export boundary
4. Run the documented install, build, test, and lint commands where practical.
5. Run or attempt this CLI smoke path in a clean temporary workspace:

```bash
prudentia doctor
prudentia create --title "Palindrome checker" --course "CS101" --topic "strings and functions" --difficulty beginner
prudentia generate --all
prudentia validate --allow-native-execution
prudentia simulate --profiles weak,partial,misconception
prudentia report
prudentia export student
prudentia export teacher
prudentia status
```

If the command name differs, use the repository's documented equivalent and note the difference.

If Docker is unavailable in the review environment, inspect whether Docker is still the production default and whether native execution is an explicit escape hatch only.

6. Inspect generated artifacts and ZIP contents if the smoke path succeeds.
7. Inspect failure modes if the smoke path fails. Determine whether the failure is environmental, documentation-related, or a real implementation gap.
8. Review automated tests for meaningful coverage of workspace creation, schema validation, generation, validation, simulation, export safety, credential scanning, and CLI smoke behavior.
9. Review security-sensitive code manually: path normalization, workspace write restrictions, sandbox execution, context manifests, logs, export allowlists, leak scanners, and credential handling.
10. Compare repositories directly and produce a ranked verdict.

## Hard Disqualifiers

Call out any repository as unfit for production foundation if it has one or more of these issues:

- student export can include `solution/**`, `tests/hidden/**`, `reports/**`, `.prudentia/**`, or `.codex/**`
- teacher export can include credentials, `.codex/**`, auth files, API keys, session tokens, or action logs/context manifests
- generated or simulated code runs directly in the source workspace by default
- native execution is the default without explicit teacher approval
- the app asks for ChatGPT passwords, session cookies, OAuth tokens, or OpenAI API keys in its own UI
- Codex integration reads, copies, parses, uploads, or exposes `~/.codex/auth.json`
- workspace writes allow path traversal outside the assignment root
- critical workflows are fake, stubbed, or only mocked while appearing complete
- there is no meaningful path to create, validate, and export an assignment

A disqualified repository can still be scored for learning value, but it should not be recommended as the base to continue from.

## Scorecard

Score each category from 0 to 5, then apply the weight.

Use this scale:

- 0: absent or misleading
- 1: skeletal, mostly nonfunctional, or unsafe
- 2: partially implemented with major gaps
- 3: usable but incomplete or fragile
- 4: solid production-shaped MVP with manageable gaps
- 5: excellent implementation with strong evidence and low residual risk

Weighted categories:

| Category | Weight | What To Judge |
| --- | ---: | --- |
| Requirements fidelity | 30 | FR-001 through FR-020, NFR-001 through NFR-012, acceptance test, local-first scope, out-of-scope discipline |
| Architecture and design | 25 | clear ownership boundaries, dependency direction, contracts, cohesive modules, no speculative layers, maintainable change path |
| Correctness and safety | 20 | workspace safety, sandbox model, export scanner, credential handling, context privacy, repair bounds, deterministic behavior |
| Tests and verification | 15 | automated coverage, smoke path, meaningful assertions, export leak tests, test-runner tests, CI portability |
| Developer and teacher operability | 10 | install docs, doctor command, readable errors, CLI usability, UI workflow completeness, accessibility, SECURITY docs |

Calculate:

```text
weighted_score = (requirements * 30) + (architecture * 25) + (correctness * 20) + (tests * 15) + (operability * 10)
maximum = 500
```

## Requirement Coverage Matrix

For each repo, mark each item:

- `pass`: implemented and verified
- `partial`: implemented with material gaps
- `fail`: absent, broken, or contradicted
- `unknown`: could not verify

Cover at least:

```text
FR-001 doctor/readiness
FR-002 workspace creation
FR-003 course profile
FR-004 Codex readiness without credential inspection
FR-005 context preview
FR-006 brief generation
FR-007 starter generation
FR-008 solution generation
FR-009 visible and hidden test generation
FR-010 rubric generation
FR-011 validation
FR-012 bounded repair loop
FR-013 simulation
FR-014 reports
FR-015 teacher approval
FR-016 student export
FR-017 teacher export
FR-018 action log
FR-019 checkpoints
FR-020 manual editing reflection

NFR-001 local-first
NFR-002 privacy
NFR-003 credential safety
NFR-004 sandboxing
NFR-005 reliability/checkpoints
NFR-006 reproducibility/run records
NFR-007 maintainability
NFR-008 extensibility without weakening Python/pytest
NFR-009 accessibility
NFR-010 performance
NFR-011 transparency
NFR-012 security logging/redaction
```

## Architecture Review Lenses

For each repo, answer:

1. What is the direct path from teacher input to validated exports?
2. Which modules own durable boundaries, and are those boundaries honest?
3. Is business logic duplicated between CLI, server, and UI?
4. Are file paths normalized and constrained at the workspace boundary?
5. Does the Codex boundary isolate SDK or CLI volatility from the rest of the app?
6. Does the context manifest model preserve privacy and teacher visibility?
7. Does validation combine deterministic artifact checks with pytest execution?
8. Does the test runner use an ephemeral copy and avoid source workspace writes?
9. Is export packaging allowlist-driven for student packages?
10. Are logs and manifests useful without leaking secrets?
11. Does the UI implement a guided workbench rather than a chat interface?
12. Are abstractions driven by current MVP needs, or are they speculative?

Classify major abstractions as:

- essential boundary
- useful local simplification
- pass-through layer
- speculative abstraction
- stale or fake support surface

## Evidence Requirements

Use concrete evidence:

- file references with line numbers where possible
- command outputs summarized accurately
- ZIP content inspection results
- failing tests or stack traces summarized briefly
- examples of strong and weak design decisions

Separate:

- facts verified in code or by commands
- inferences from code structure
- assumptions because something could not be run

## Output Format

Write the final review in Markdown with this structure.

### 1. Executive Verdict

State the winner, ranking, and whether the winner is production-shaped enough to continue from.

Example:

```text
Winner: Repo B
Ranking: B > A > C
Recommendation: Continue from Repo B, borrow Repo A's export tests, discard Repo C as a foundation.
```

### 2. Score Summary

| Repo | Requirements /5 | Architecture /5 | Correctness Safety /5 | Tests /5 | Operability /5 | Weighted /500 | Verdict |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| A |  |  |  |  |  |  |  |
| B |  |  |  |  |  |  |  |
| C |  |  |  |  |  |  |  |

### 3. Disqualifiers Or Critical Risks

List any hard disqualifiers first. If none, say so.

### 4. Requirement Coverage

Provide a compact matrix for FR and NFR coverage. Keep detailed notes only for failed, partial, or unknown items.

### 5. Architecture Comparison

Compare the three designs directly:

- strongest ownership model
- cleanest workflow orchestration
- strongest filesystem and workspace boundary
- best Codex isolation
- best validation/test-runner boundary
- strongest export design
- best UI approach
- least speculative complexity

### 6. Repository Findings

For each repo:

```text
Repo A
- Strengths:
- Production blockers:
- Requirement gaps:
- Architecture issues:
- Test and verification gaps:
- Notable files:
- Commands run:
- Residual risk:
```

Repeat for Repo B and Repo C.

### 7. Acceptance Test Results

Show the install/build/test/lint/smoke result for each repo.

Use:

- `pass`
- `fail`
- `not run`
- `environment blocked`

Explain failures in one or two sentences each.

### 8. Best Ideas To Preserve

Identify any implementation ideas worth borrowing from losing repos. Do not recommend merging code unless the ownership boundaries and licenses make that safe.

### 9. Fix-Now Roadmap For The Winner

Give a short prioritized roadmap:

- fix now
- next pass
- optional later
- do not touch yet

### 10. Final Recommendation

Make a clear call:

- which repo should become the base
- whether it is ready for production hardening or needs foundational repair first
- what must be fixed before any public MVP release

Keep the conclusion direct. Do not hedge unless evidence is genuinely incomplete.

## Tie-Breakers

If two repositories are close, prefer the one with:

1. safer export and credential boundaries
2. clearer workspace and test-runner contracts
3. more complete CLI smoke path
4. stronger tests for core behaviors
5. less speculative architecture
6. simpler future path to live Codex SDK changes
7. better teacher-facing workflow clarity

Do not use UI polish, framework popularity, or code volume as tie-breakers unless the core product and safety requirements are already comparable.
