# Prudentia — Product Idea and MVP Requirements Specification

Version 0.1 — MVP product requirements

Date: 2 May 2026

| Field | Value |
| --- | --- |
| Product type | Open-source, local-first CS assignment workbench for teachers. |
| AI integration | Uses locally authenticated Codex capabilities to generate and revise assignment artifacts. |
| Primary user | Computer science teacher creating programming assignments. |
| MVP platform | Local web UI plus CLI commands on the teacher's machine. |
| MVP language support | Python 3.12 assignments using pytest. |
| Core value | Transforms Codex from a general coding agent into a structured assignment build system with validation, simulation, safety checks, and export packaging. |

This document defines what the MVP must do and what must be true for users. Implementation structure, package boundaries, stack choices, and build sequencing belong in `prompts/implementation.md`.

## 1. Executive summary

Prudentia is a local-first assignment production system for computer science teachers. It helps a teacher create a complete programming assignment package: student brief, starter code, reference solution, visible tests, hidden tests, rubric, simulated student submissions, validation report, and exportable student/teacher ZIP packages.

Prudentia is not a generic chatbot, prompt library, or thin wrapper around Codex. Codex performs agentic code and content generation. Prudentia supplies the deterministic workflow around Codex: workspace schema, generation sequence, validation rules, sandboxed test execution, simulation matrix, export scanner, teacher approval gates, and local audit trail.

The MVP is local-only. It does not require a Prudentia cloud account, does not store student data centrally, and does not handle ChatGPT passwords or session cookies. The teacher authenticates Codex using Codex-supported local authentication outside Prudentia.

### 1.1 Product thesis

Codex can already generate code, tests, and prose. The unique value of Prudentia is making the assignment-creation process repeatable, reviewable, export-safe, and education-specific. The product should be judged by whether a teacher can reliably ship a clean assignment package, not by whether the AI can produce one-off files.

### 1.2 MVP success definition

The MVP is successful when a teacher can run one local command or use one local UI flow to produce a validated Python/pytest assignment package whose reference solution passes tests, whose simulated submissions produce meaningful signal, and whose student export excludes solution files, hidden tests, private notes, and AI logs.

## 2. Product boundaries

### 2.1 In scope for MVP

- Local web UI launched from a CLI command.
- CLI commands for create, generate, validate, simulate, report, and export.
- Codex integration through the local Prudentia runtime.
- Teacher-managed Codex authentication; Prudentia does not collect OpenAI credentials.
- Python 3.12 + pytest assignment generation and validation.
- Assignment workspace schema with deterministic folders and metadata.
- Docker-based sandboxed test execution with network disabled by default.
- Visible tests, hidden tests, reference solution, starter code, rubric, and teacher report.
- Three simulated student submissions: weak, partial, and common-misconception.
- Student and teacher ZIP exports with deterministic exclusion rules.

### 2.2 Out of scope for MVP

- Cloud-hosted SaaS workflow.
- Multi-user classroom management.
- LMS integrations such as Canvas, Moodle, Blackboard, or Google Classroom.
- Real student submission grading.
- Gradebook passback.
- Plagiarism detection.
- Institution admin dashboard.
- Java, JavaScript, SQL, C/C++, or other language adapters.
- Automated dependency installation without teacher approval.
- Any workflow that uses user ChatGPT credentials as a hosted proxy for Prudentia.

### 2.3 Non-negotiable product constraints

- Local-first by default: no Prudentia-hosted backend is needed for MVP workflows.
- Teacher remains final authority: AI-generated material is draft until approved.
- No credential handling: Prudentia never requests ChatGPT password, session cookie, OAuth token, or API key directly.
- Context transparency: before a Codex task, Prudentia shows the file manifest and teacher-controlled context included in that task.
- Export safety: student exports must never contain solution, hidden tests, private notes, run logs, or AI history unless explicitly overridden through a dangerous advanced flow. The MVP should not implement that override.

## 3. MVP system model

The MVP runs locally on the teacher's machine. It provides a browser-based workbench and CLI commands. It stores each assignment as a portable local workspace folder, uses the teacher's existing local Codex authentication, runs generated Python code in a sandboxed test path by default, and creates separate student and teacher export packages.

```text
Teacher machine
  ├─ Browser at http://127.0.0.1:<port>
  │    └─ Prudentia local web UI
  ├─ prudentia CLI
  ├─ Local Prudentia service
  │    ├─ Workspace state and artifact generation
  │    ├─ Codex task orchestration
  │    ├─ Validation and test execution
  │    ├─ Simulation and reporting
  │    └─ Export packaging and safety scanning
  ├─ Assignment workspace folder
  ├─ Local Codex installation and auth
  └─ Docker engine for sandboxed pytest execution
```

### 3.1 System requirements

- All MVP workflows run without a Prudentia-hosted backend.
- The local web UI and CLI operate on the same workspace state.
- Workspace state is stored in local files that travel with the assignment.
- Codex activity is bounded to the active assignment workspace and visible through context previews.
- Validation never trusts generated artifacts without deterministic checks and test execution.
- Export packaging is a distinct safety step, not a copy of the workspace folder.

## 4. Codex integration requirements

Prudentia uses locally authenticated Codex capabilities for bounded workflow steps. Codex can generate or revise assignment artifacts, but Prudentia owns the workspace structure, context preview, validation, simulation, approval gates, reporting, and export safety.

### 4.1 Usage rules

- Each AI-assisted workflow step has a recorded task kind, input context manifest, output summary, changed files, and unresolved issues.
- Planning and review tasks should not write assignment artifacts unless the teacher explicitly starts a generation or repair step.
- Generation and repair tasks may write only inside the active assignment workspace.
- Prudentia does not modify the user's global Codex configuration.
- Prudentia may create project-scoped Codex settings inside the assignment workspace when needed for conservative sandbox defaults.
- Prudentia must never parse, copy, upload, or expose `~/.codex/auth.json`.
- Prudentia must never ask for ChatGPT passwords, session cookies, OAuth tokens, or OpenAI API keys in its own UI.
- If Codex is unavailable, the UI must allow non-AI editing and show a clear remediation path: install Codex, authenticate Codex locally, then rerun doctor.

### 4.2 Context preview

Before starting a Codex task, Prudentia shows:

- task kind
- included files
- why each file is included
- file role: student-visible, teacher-only, metadata, test, or report
- excluded globs
- allowed write globs
- privacy warnings

## 5. Assignment workspace schema

Every assignment is a portable local folder. The folder is the source of truth. No external database is required for MVP.

```text
<assignment-slug>/
  prudentia.yaml
  brief.md
  README.student.md
  rubric.md
  pyproject.toml
  starter/
    src/
      assignment.py
  solution/
    src/
      assignment.py
  tests/
    visible/
      test_basic.py
    hidden/
      test_edge_cases.py
  simulations/
    weak/
      src/assignment.py
    partial/
      src/assignment.py
    misconception/
      src/assignment.py
  reports/
    teacher_report.md
    validation_report.json
    simulation_matrix.md
  exports/
    student/
    teacher/
  .codex/
    config.toml
  .prudentia/
    action_log.jsonl
    workflow_state.json
    context_manifests/
    runs/
    checkpoints/
    export_manifests/
```

### 5.1 prudentia.yaml schema

```yaml
schema_version: "0.1"
id: "uuid-v4"
title: "Palindrome checker"
slug: "palindrome-checker"
created_at: "2026-05-02T12:00:00Z"
updated_at: "2026-05-02T12:30:00Z"
course:
  name: "CS101"
  level: "introductory"
  audience: "first-year undergraduate"
language:
  id: "python"
  version: "3.12"
test_framework:
  id: "pytest"
  version_constraint: ">=8"
assignment:
  topic: "strings and functions"
  difficulty: "beginner"
  estimated_minutes: 45
  learning_objectives:
    - "Write pure functions with clear input/output behavior"
    - "Handle common string edge cases"
policy:
  ai_context_allowlist:
    - "brief.md"
    - "rubric.md"
    - "starter/**"
    - "solution/**"
    - "tests/**"
  never_send:
    - "exports/**"
    - ".prudentia/action_log.jsonl"
    - "reports/**"
  student_export_exclude:
    - "solution/**"
    - "tests/hidden/**"
    - "reports/**"
    - ".prudentia/**"
    - ".codex/**"
status:
  brief: "draft"
  starter: "draft"
  solution: "draft"
  tests: "draft"
  rubric: "draft"
  validation: "not_run"
  export: "not_ready"
```

### 5.2 Artifact status values

| Status | Meaning |
| --- | --- |
| draft | Generated or edited but not approved by teacher. |
| approved | Teacher accepted artifact as suitable for use. |
| not_run | Validation step has not executed. |
| passed | Validation completed successfully. |
| failed | Validation failed and must be repaired or acknowledged. |
| not_ready | Export is blocked because required artifacts are missing or unapproved. |
| ready | Export scanner passed and package can be built. |

## 6. User workflows

### 6.1 Primary workflow: generate complete assignment

1. Teacher runs prudentia ui or prudentia create from a terminal.
1. Teacher enters title, course, topic, difficulty, learning objectives, estimated duration, and constraints.
1. Prudentia creates the workspace folders, assignment metadata, conservative local execution settings, and initial context manifest.
1. Prudentia checks Codex readiness. If not ready, teacher sees setup instructions and can continue with manual editing only.
1. Teacher previews context and starts Generate All.
1. Prudentia runs Codex tasks in sequence: plan, brief, starter, solution, tests, rubric.
1. Prudentia validates required files and runs visible plus hidden tests against the reference solution.
1. If tests fail, Prudentia allows up to two Codex repair attempts, each followed by validation.
1. Prudentia generates three simulated submissions and runs tests against each.
1. Prudentia generates teacher_report.md and simulation_matrix.md.
1. Teacher reviews artifacts, approves them, and exports student and teacher packages.

### 6.2 Secondary workflow: validate existing assignment

1. Teacher opens an existing workspace.
1. Prudentia reads prudentia.yaml and checks required folders.
1. Teacher runs Validate.
1. Prudentia executes pytest against solution and simulations through the configured sandbox path.
1. Prudentia updates reports/validation_report.json and shows actionable errors.

### 6.3 Secondary workflow: export packages

1. Teacher opens export screen or runs prudentia export student / prudentia export teacher.
1. Prudentia runs export scanner.
1. If student export contains forbidden files, export is blocked.
1. Student package is written to exports/student/&lt;slug&gt;-student.zip.
1. Teacher package is written to exports/teacher/&lt;slug&gt;-teacher.zip.
1. Export manifest is written to .prudentia/export_manifests/&lt;timestamp&gt;.json.

## 7. CLI and local automation surface

The MVP must expose a thin command-line path for core workflows so a teacher or coding agent can validate the system without using the UI.

```bash
prudentia doctor
prudentia ui [--port 4898]
prudentia create --title "Palindrome checker" --course CS101 --topic "strings" --difficulty beginner
prudentia generate --all
prudentia generate --brief|--starter|--solution|--tests|--rubric
prudentia validate
prudentia simulate --profiles weak,partial,misconception
prudentia report
prudentia export student
prudentia export teacher
prudentia status
prudentia clean-runs
```

The local web UI must support the same workflow operations. Long-running workflows must expose readable progress and terminal success or failure states.

## 8. Required capabilities

The MVP must provide these capabilities as clearly separable user-visible behaviors:

- create and reopen assignment workspaces
- preview AI task context before generation or repair
- generate assignment artifacts
- validate artifacts and run tests
- generate and evaluate simulated submissions
- produce teacher-facing reports
- package student and teacher exports
- record local workflow history and errors
- block unsafe exports

## 9. Generation and validation pipeline

### 9.1 Generate All requirements

Generate All must create or refresh the complete assignment package in a bounded, reviewable workflow:

- checkpoint the workspace before modifying generated artifacts
- preview context before AI-assisted steps
- generate the brief, starter code, reference solution, visible tests, hidden tests, and rubric
- validate required files after generation
- run the reference solution against visible and hidden tests
- attempt bounded repair if reference validation fails
- update artifact statuses and local workflow history

### 9.2 Repair loop

The repair loop is bounded. Prudentia must not enter indefinite agent loops.

- A failed reference validation may trigger at most two repair attempts.
- Repair uses the validation report, failing test output, brief, reference solution, and tests as context.
- Repair writes only to solution and test artifacts.
- Each repair attempt is followed by validation.
- If validation still fails, the assignment requires teacher review.

### 9.3 Artifact validation rules

- brief.md must include title, learning objectives, task description, input/output expectations, constraints, and submission instructions.
- starter/src/assignment.py must exist and must not contain a complete reference implementation.
- solution/src/assignment.py must exist and must pass all visible and hidden tests.
- tests/visible/test_basic.py must exist and contain at least three pytest tests.
- tests/hidden/test_edge_cases.py must exist and contain at least three pytest tests.
- rubric.md must include criteria, point values, and common mistakes.
- teacher_report.md must include validation result, simulation matrix summary, and unresolved issues.

## 10. Test runner and sandbox model

MVP test execution uses Docker by default. Native local execution is disabled unless the teacher explicitly uses --allow-native-execution. This avoids silent execution of generated or simulated code on the host machine.

### 10.1 Docker execution invariants

The exact test command may vary. The invariant is fixed: no network, no host writes except the explicit run result directory, and no execution outside the ephemeral run copy.

The Docker runner must:

- run tests against an ephemeral workspace copy
- disable network access
- avoid writing to the source workspace
- capture stdout, stderr, exit code, test report, and run metadata
- expose actionable failure output to the teacher

### 10.2 Run records

Each validation run records enough information for review and reproduction:

- ephemeral workspace copy location
- stdout and stderr
- exit code
- pytest report
- run metadata

### 10.3 Native execution escape hatch

- CLI flag: --allow-native-execution.
- UI: hidden under Advanced Settings with explicit warning.
- Native mode may run only pytest for Python MVP.
- Native mode must still operate on an ephemeral run copy, not the source workspace.

## 11. Export packaging

### 11.1 Student package

Student package path: exports/student/&lt;slug&gt;-student.zip

```text
Included:
  brief.md
  README.student.md
  pyproject.toml
  starter/**
  tests/visible/**

Excluded:
  solution/**
  tests/hidden/**
  simulations/**
  reports/**
  exports/**
  .prudentia/**
  .codex/**
  rubric.md unless teacher explicitly marks it student-visible
```

### 11.2 Teacher package

Teacher package path: exports/teacher/&lt;slug&gt;-teacher.zip

```text
Included:
  brief.md
  README.student.md
  rubric.md
  pyproject.toml
  starter/**
  solution/**
  tests/**
  simulations/**
  reports/**
  prudentia.yaml

Excluded:
  exports/**
  .prudentia/action_log.jsonl
  .prudentia/context_manifests/**
  .codex/**
  local auth, tokens, credential files, OS temp files
```

### 11.3 Export scanner invariants

- Student export is blocked if any path matches solution/**, tests/hidden/**, reports/**, .prudentia/**, or .codex/**.
- Student export is blocked if file contents match obvious solution leak markers such as "REFERENCE SOLUTION", "hidden test", or paths to solution files.
- Teacher export is blocked if any credential-like string is detected: OPENAI_API_KEY, sk-, session token markers, or auth.json.
- Every export writes an export_manifest.json listing included and excluded files plus scanner results.

## 12. Functional requirements

| ID | Requirement | Acceptance criterion |
| --- | --- | --- |
| FR-001 | Local startup | prudentia doctor verifies local runtime, Codex availability, Docker availability, and Python test runner readiness. |
| FR-002 | Workspace creation | Create deterministic workspace folders, assignment metadata, local execution settings, and initial workflow state. |
| FR-003 | Course profile | Capture course name, level, audience, topic, difficulty, constraints, and learning objectives. |
| FR-004 | Codex readiness | Check local Codex availability without inspecting credentials directly. |
| FR-005 | Context preview | Show files and metadata that will be included in each Codex task before execution. |
| FR-006 | Brief generation | Generate brief.md with objectives, task, constraints, examples, submission instructions, and grading notes. |
| FR-007 | Starter generation | Generate starter/src/assignment.py with skeletons and TODOs, not full solution logic. |
| FR-008 | Solution generation | Generate solution/src/assignment.py as teacher-only reference solution. |
| FR-009 | Test generation | Generate visible and hidden pytest tests with normal and edge cases. |
| FR-010 | Rubric generation | Generate rubric.md with point values, criteria, and common mistakes. |
| FR-011 | Validation | Run deterministic checks and pytest against the reference solution. |
| FR-012 | Repair loop | Attempt at most two Codex repairs for failed reference validation. |
| FR-013 | Simulation | Generate weak, partial, and misconception submissions and validate them. |
| FR-014 | Report generation | Write teacher_report.md, validation_report.json, and simulation_matrix.md. |
| FR-015 | Teacher approval | Allow teacher to approve generated artifacts; export is blocked until required artifacts are approved or explicitly marked accepted. |
| FR-016 | Student export | Create student ZIP and block forbidden files. |
| FR-017 | Teacher export | Create teacher ZIP and block credentials/log leaks. |
| FR-018 | Action log | Write local JSONL events for workflows, validations, exports, and errors. |
| FR-019 | Checkpoints | Create checkpoint before Generate All and before repair loop. |
| FR-020 | Manual editing | Allow local editing of generated Markdown/code through filesystem and reflect status in UI. |

## 13. Non-functional requirements

| ID | Requirement | Acceptance criterion |
| --- | --- | --- |
| NFR-001 | Local-first | All MVP workflows run on the teacher machine with no Prudentia cloud dependency. |
| NFR-002 | Privacy | No central storage; context preview before AI task; never-send globs respected. |
| NFR-003 | Credential safety | Prudentia never asks for ChatGPT password, session cookie, OAuth token, or API key. |
| NFR-004 | Sandboxing | Docker runner disables network and uses ephemeral run copies by default. |
| NFR-005 | Reliability | Failed Codex tasks must not corrupt source workspace; checkpoint before destructive workflows. |
| NFR-006 | Reproducibility | Each validation run records command, image, timestamps, exit code, and test report. |
| NFR-007 | Maintainability | Core workflow, Codex integration, test execution, validation, and export responsibilities remain clearly separated. |
| NFR-008 | Extensibility | Future language/test-framework support must not weaken the MVP Python/pytest contract. |
| NFR-009 | Accessibility | Web UI supports keyboard navigation, semantic labels, plain status text, and readable error messages. |
| NFR-010 | Performance | Workspace creation under 5 seconds; export under 10 seconds for MVP-size projects; AI time excluded. |
| NFR-011 | Transparency | UI displays that Codex/OpenAI usage is controlled by the teacher-managed local Codex setup. |
| NFR-012 | Security logging | Logs include workflow events and approval decisions but redact secrets and personal data patterns. |

## 14. Prompt and context contracts

Prudentia should use stable prompt templates for AI-assisted workflows. Prompt text should be versioned in the implementation and include a product-specific control block plus the context manifest path.

### 14.1 Global task instruction

Every AI task instruction must require Codex to:

- operate only inside the current assignment workspace
- use the context manifest as the source of truth for allowed files
- avoid reading or writing outside the assignment workspace
- keep teacher-only solution and hidden tests out of student-facing files
- prefer simple, teachable code over clever code
- report changed files, assumptions, unresolved issues, and recommended next action

### 14.2 Context manifest requirements

The context manifest must include:

- schema version
- manifest ID
- workspace ID
- task kind
- creation timestamp
- included files with path, reason, and role
- excluded globs
- allowed write globs
- privacy warnings

## 15. Local web UI requirements

The web UI is not a chat interface. It is a guided workbench. Chat-like freeform prompting is out of scope for MVP.

| Screen | Required controls |
| --- | --- |
| Home / Workspaces | Open existing workspace; create new workspace; run doctor. |
| Create assignment | Course, title, topic, difficulty, learning objectives, estimated time, constraints. |
| Generate | Generate All; individual generation buttons; context preview; progress events. |
| Review artifacts | Tabs for brief, starter, solution, tests, rubric; approve buttons; status badges. |
| Validate | Run validation; show pytest results; show repair option when failed. |
| Simulate | Generate simulations; run tests; show matrix. |
| Export | Student export; teacher export; export scanner result; package links. |
| Settings | Workspace path, Docker/native execution setting, never-send globs, Codex readiness. |

## 16. Security and privacy requirements

### 16.1 Credential handling

- Do not ask for OpenAI API keys in the MVP UI.
- Do not ask for ChatGPT credentials or cookies.
- Do not read ~/.codex/auth.json.
- Do not export .codex or global credential files.
- Codex auth setup instructions must direct the user to local Codex authentication, not Prudentia forms.

### 16.2 File and path safety

- Normalize all paths and reject path traversal attempts.
- All writes must remain under workspace root.
- Exporter uses allowlist for student package, not only blocklist.
- Action logs must redact patterns containing API keys, tokens, passwords, and credential paths.
- Teacher must approve native execution if Docker is unavailable.

### 16.3 Student data boundary

MVP does not process real student submissions. The simulations folder contains AI-generated fake submissions only. Any UI label must say simulated submissions, not student submissions. Real student grading is post-MVP and requires separate privacy, compliance, and policy design.

## 17. MVP acceptance test

Engineering should use this end-to-end demo as the MVP acceptance test.

```bash
# Preconditions
codex is installed and authenticated locally
Docker is installed and running
the supported local runtime is installed

# Demo
prudentia doctor
prudentia create   --title "Palindrome checker"   --course "CS101"   --topic "strings and functions"   --difficulty beginner
cd palindrome-checker
prudentia generate --all
prudentia validate
prudentia simulate --profiles weak,partial,misconception
prudentia report
prudentia export student
prudentia export teacher

# Required result
exports/student/palindrome-checker-student.zip exists
exports/teacher/palindrome-checker-teacher.zip exists
solution/src/assignment.py passes visible and hidden tests
reports/teacher_report.md exists
reports/simulation_matrix.md exists
student ZIP does not contain solution/**, tests/hidden/**, reports/**, .prudentia/**, or .codex/**
```

### 17.1 Done means

- The demo works on at least one clean macOS or Linux developer machine.
- Automated tests cover core metadata, export scanner, and workspace creation.
- At least one example assignment exists in examples/.
- README has installation, Codex setup, Docker setup, and demo instructions.
- SECURITY.md documents local execution risks and how to report issues.

## 18. MVP release readiness

The MVP is release-ready when:

- workspace creation, generation, validation, simulation, reporting, and export work from the CLI
- the same workflows are available through the local web UI
- student export safety checks pass
- teacher export credential checks pass
- core workspace, validation, and export behavior is covered by automated tests
- a clean developer machine can run the documented demo after installing prerequisites
- README and SECURITY documentation explain setup, local execution risks, Codex setup, Docker setup, and issue reporting

## 19. Post-MVP roadmap

- Additional language adapters: Java/JUnit, JavaScript/TypeScript/Vitest, SQL, C/C++.
- VS Code extension that opens the Prudentia workspace panel.
- Assignment template marketplace or community template registry.
- LMS export adapters for Canvas, Moodle, Blackboard, Google Classroom, and GitHub Classroom.
- Optional cloud sync for templates and team collaboration.
- Institution edition with admin policies, managed API billing options, and audit logs.
- Real student submission grading after separate privacy, compliance, bias, and review design.

## 20. Open-source project policy

Recommended default license is Apache-2.0 unless the founder decides that AGPL-style protection against closed hosted forks is more important than adoption. MVP repository should include LICENSE, README.md, CONTRIBUTING.md, SECURITY.md, and docs/data-privacy.md.

The open-source core should include local workspace management, Codex orchestration, sandboxed validation, and exports. Future paid or hosted layers should be separate from the MVP core and should not change local-first guarantees.

## 21. Key risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Teachers can already use Codex directly. | Differentiate through deterministic workflow, validation, simulation, export scanner, and teacher-friendly UI. |
| Codex output may be wrong. | Validate required files, run tests, create simulation matrix, require teacher approval. |
| Running generated code is risky. | Docker sandbox, no network, ephemeral run copies, native execution opt-in only. |
| Student export may leak solution. | Allowlist export, forbidden path scanner, content leak scanner, export manifest. |
| Install friction. | doctor command, clear setup docs, local web UI, example assignment. |
| Codex SDK/API changes. | Keep Codex integration isolated behind a single integration boundary with integration tests. |
| Privacy concerns. | No cloud in MVP; context preview; no real student grading. |

## 22. Source basis

The following external assumptions are based on official OpenAI developer documentation accessed on 2 May 2026:

- Codex SDK documentation: programmatically control local Codex agents. https://developers.openai.com/codex/sdk
- Codex CLI documentation: local Codex can read, change, and run code on the user machine in the selected directory; CLI setup uses local authentication. https://developers.openai.com/codex/cli
- Codex authentication documentation: Codex supports ChatGPT sign-in for subscription access and API-key sign-in for usage-based access; API-key use is billed through the OpenAI Platform. https://developers.openai.com/codex/auth
- Codex agent approvals and security documentation: local Codex uses sandbox and approval controls; defaults include no network access and write permissions limited to the active workspace. https://developers.openai.com/codex/agent-approvals-security
- Codex configuration reference: project-scoped sandbox configuration. https://developers.openai.com/codex/config-reference
