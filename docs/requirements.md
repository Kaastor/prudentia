# Prudentia — Product Idea and MVP Requirements Specification

Version 0.1 — Implementation-ready draft

Date: 2 May 2026

| Field | Value |
| --- | --- |
| Product type | Open-source, local-first CS assignment workbench for teachers. |
| AI integration | Uses the OpenAI Codex SDK from a local Node.js backend to control local Codex agents. |
| Primary user | Computer science teacher creating programming assignments. |
| MVP platform | Local web UI served by a TypeScript/Node backend, plus CLI commands. |
| MVP language support | Python 3.12 assignments using pytest. |
| Core value | Transforms Codex from a general coding agent into a structured assignment build system with validation, simulation, safety checks, and export packaging. |

This document intentionally chooses a concrete MVP architecture. Post-MVP options are listed separately so engineering can start without open architectural questions.

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
- Codex SDK integration through a local Node.js backend.
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

## 3. Canonical MVP architecture

The MVP uses a local TypeScript/Node backend. The backend serves the local web UI, exposes local HTTP endpoints, owns workspace state, invokes the Codex SDK, runs sandboxed tests, and creates exports. The frontend is a browser UI opened against localhost. The CLI starts the server and also exposes direct command-line operations.

```text
Teacher machine
  ├─ Browser at http://127.0.0.1:<port>
  │    └─ Prudentia React UI
  ├─ prudentia CLI
  ├─ Local Node.js backend
  │    ├─ Workspace Manager
  │    ├─ Codex Orchestrator using @openai/codex-sdk
  │    ├─ Context Manifest Builder
  │    ├─ Artifact Validator
  │    ├─ Docker Test Runner
  │    ├─ Simulation Runner
  │    ├─ Report Generator
  │    └─ Export Packager
  ├─ Assignment workspace folder
  ├─ Local Codex installation and auth
  └─ Docker engine for sandboxed pytest execution
```

### 3.1 Technology decisions

| Area | MVP decision | Reason |
| --- | --- | --- |
| Runtime | Node.js 20+ with TypeScript | The official Codex TypeScript SDK requires server-side Node.js 18 or later; Node 20+ is a conservative implementation baseline. |
| Codex integration | @openai/codex-sdk | Programmatically controls local Codex agents from Prudentia workflows. |
| UI | React + Vite local web UI | Fast local UI with no cloud dependency. |
| Backend | Fastify local HTTP server | Small, typed, and suitable for local APIs and SSE progress events. |
| CLI | Commander-based TypeScript CLI | Simple command surface for power users and automation. |
| State | Local YAML/JSON/JSONL files in workspace | No database needed for MVP; state travels with assignment. |
| Validation | Zod schemas plus deterministic file checks | Codex output is never trusted without validation. |
| Sandbox | Docker runner with --network=none | Reduces risk when running generated code and simulations. |
| Export | ZIP packages; Markdown reports | MVP avoids PDF complexity and focuses on reliable packaging. |

### 3.2 Repository layout

```text
prudentia/
  apps/
    cli/                  # prudentia command
    web/                  # React local web UI
    local-server/          # Fastify backend
  packages/
    core/                  # domain models and workflow state machine
    codex-adapter/          # @openai/codex-sdk integration
    workspace/              # file schema, manifests, checkpoints
    validators/             # artifact and export validators
    runner-docker/           # sandboxed pytest runner
    generators/             # prompt contracts and orchestration plans
    exporters/              # student/teacher ZIP packagers
    reporting/              # teacher report and run summaries
    templates-python-pytest/ # MVP template
  examples/
    palindrome-python-pytest/
  docs/
    architecture.md
    data-privacy.md
    sandboxing.md
    codex-sdk-integration.md
  tests/
  package.json
  pnpm-workspace.yaml
  README.md
  SECURITY.md
  LICENSE
```

## 4. Codex SDK integration contract

Prudentia uses the Codex SDK as the agent-control layer. The backend starts Codex threads for bounded workflow steps and instructs Codex to edit only the current assignment workspace. Prudentia validates the generated files after every step and never assumes that Codex output is correct.

### 4.1 External source assumptions

- OpenAI documents the Codex SDK as a way to programmatically control local Codex agents and integrate Codex into applications, workflows, and internal tools.
- The TypeScript SDK is installed as @openai/codex-sdk and is intended for server-side Node.js 18 or later.
- Codex supports ChatGPT sign-in for subscription access and API-key sign-in for usage-based access; Prudentia delegates authentication to the user-managed local Codex setup.
- Codex local execution uses sandbox and approval controls; Prudentia should create conservative project-scoped defaults and still perform its own export/test safeguards.

### 4.2 CodexAdapter interface

```ts
export interface CodexAdapter {
  checkReadiness(workspaceRoot: string): Promise<CodexReadiness>;
  runTask(input: CodexTaskInput): Promise<CodexTaskResult>;
}

export type CodexTaskKind =
  | 'PLAN_ASSIGNMENT'
  | 'GENERATE_BRIEF'
  | 'GENERATE_STARTER'
  | 'GENERATE_SOLUTION'
  | 'GENERATE_TESTS'
  | 'REPAIR_REFERENCE_SOLUTION'
  | 'GENERATE_RUBRIC'
  | 'GENERATE_SIMULATIONS'
  | 'REVIEW_ASSIGNMENT_QUALITY';

export interface CodexTaskInput {
  workspaceRoot: string;
  taskKind: CodexTaskKind;
  prompt: string;
  contextManifestPath: string;
  allowedWriteGlobs: string[];
  expectedArtifacts: string[];
  mode: 'read-only' | 'workspace-write';
}

export interface CodexTaskResult {
  taskId: string;
  threadId: string;
  startedAt: string;
  finishedAt: string;
  status: 'succeeded' | 'failed' | 'requires_teacher_review';
  summary: string;
  changedFiles: string[];
  unresolvedIssues: string[];
}
```

### 4.3 SDK usage rules

- Each workflow step gets a new Codex task record and a context manifest.
- Planning and review tasks use read-only mode whenever possible.
- Generation and repair tasks use workspace-write mode limited to the assignment workspace.
- Prudentia does not modify the user global Codex configuration.
- Prudentia may write project-scoped .codex/config.toml inside the assignment workspace with conservative sandbox defaults.
- Prudentia must never parse, copy, upload, or expose ~/.codex/auth.json.
- If Codex is unavailable, the UI must allow non-AI editing and show a clear remediation path: install Codex, authenticate Codex, then rerun doctor.

### 4.4 Project-scoped Codex configuration

When a workspace is created, Prudentia writes a conservative project-scoped Codex configuration. If Codex requires the user to trust project-scoped config, Prudentia should display that as setup guidance rather than bypassing it.

```toml
# <workspace>/.codex/config.toml
sandbox_mode = "workspace-write"
approval_policy = "on-request"

[sandbox_workspace_write]
network_access = false
writable_roots = ["."]
exclude_slash_tmp = true
exclude_tmpdir_env_var = true
```

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
1. Prudentia creates workspace folders, prudentia.yaml, .codex/config.toml, and initial context manifest.
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
1. Docker runner executes pytest against solution and simulations.
1. Prudentia updates reports/validation_report.json and shows actionable errors.

### 6.3 Secondary workflow: export packages

1. Teacher opens export screen or runs prudentia export student / prudentia export teacher.
1. Prudentia runs export scanner.
1. If student export contains forbidden files, export is blocked.
1. Student package is written to exports/student/&lt;slug&gt;-student.zip.
1. Teacher package is written to exports/teacher/&lt;slug&gt;-teacher.zip.
1. Export manifest is written to .prudentia/export_manifests/&lt;timestamp&gt;.json.

## 7. CLI and local API surface

### 7.1 CLI commands

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

### 7.2 Local HTTP endpoints

| Endpoint | Purpose |
| --- | --- |
| GET /api/health | Backend, Codex, Docker, and workspace readiness. |
| POST /api/workspaces | Create a workspace. |
| GET /api/workspaces/:id | Read workspace metadata and artifact statuses. |
| POST /api/workspaces/:id/generate | Run one generation task or Generate All. |
| POST /api/workspaces/:id/validate | Run deterministic artifact checks and pytest. |
| POST /api/workspaces/:id/simulate | Generate and validate simulated submissions. |
| POST /api/workspaces/:id/report | Create or refresh teacher report. |
| POST /api/workspaces/:id/export | Create student or teacher package. |
| GET /api/workflows/:runId/events | Server-sent events for progress streaming. |

### 7.3 Workflow event model

```ts
export interface WorkflowEvent {
  runId: string;
  workspaceId: string;
  type:
    | 'RUN_STARTED'
    | 'CODEX_TASK_STARTED'
    | 'CODEX_TASK_FINISHED'
    | 'VALIDATION_STARTED'
    | 'VALIDATION_FINISHED'
    | 'EXPORT_STARTED'
    | 'EXPORT_FINISHED'
    | 'ERROR';
  message: string;
  createdAt: string;
  payload?: Record<string, unknown>;
}
```

## 8. Component responsibilities

| Component | Responsibilities |
| --- | --- |
| CLI | Starts UI/server, runs direct workflows, prints errors, supports automation. |
| Local web UI | Guided assignment creation, context preview, progress, review, approval, export. |
| Local server | Owns HTTP API, workflow orchestration, and progress events. |
| Workspace Manager | Creates folders, writes prudentia.yaml, checkpoints, manifests, and logs. |
| Codex Orchestrator | Builds prompts, calls Codex SDK, tracks thread/task IDs, records changed files. |
| Context Manifest Builder | Determines files shown to teacher and included in Codex tasks. |
| Artifact Validator | Checks required files, schema, brief/test/rubric consistency, forbidden files. |
| Docker Test Runner | Runs pytest in isolated container with network disabled. |
| Simulation Runner | Generates weak/partial/misconception submissions and runs tests. |
| Report Generator | Writes validation report, simulation matrix, and teacher_report.md. |
| Export Packager | Creates student and teacher ZIPs with manifest and safety scan. |

## 9. Generation and validation pipeline

### 9.1 Generate All step sequence

```text
GENERATE_ALL(workspace):
  1. createCheckpoint("before-generate-all")
  2. buildContextManifest(task="PLAN_ASSIGNMENT")
  3. runCodex(PLAN_ASSIGNMENT, mode="read-only")
  4. runCodex(GENERATE_BRIEF, mode="workspace-write")
  5. validateFileExists("brief.md")
  6. runCodex(GENERATE_STARTER, mode="workspace-write")
  7. validateStarterStructure()
  8. runCodex(GENERATE_SOLUTION, mode="workspace-write")
  9. validateSolutionStructure()
 10. runCodex(GENERATE_TESTS, mode="workspace-write")
 11. validateTestStructure()
 12. runCodex(GENERATE_RUBRIC, mode="workspace-write")
 13. validateRubricStructure()
 14. runReferenceValidation()
 15. if validation fails: attemptRepair(maxAttempts=2)
 16. updateStatus()
 17. writeActionLog()
```

### 9.2 Repair loop

The repair loop is bounded. Prudentia must not enter indefinite agent loops.

```text
attemptRepair(maxAttempts=2):
  for attempt in 1..maxAttempts:
    provide Codex with:
      - validation_report.json
      - failing pytest output
      - brief.md
      - solution/src/assignment.py
      - tests/**
    allow writes only to solution/** and tests/**
    run validation again
    if validation passes: return passed
  return failed_with_teacher_review_required
```

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

### 10.1 Docker execution contract

```bash
docker run --rm \
  --network=none \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  -v <run-dir>:/workspace:ro \
  -v <result-dir>:/results:rw \
  -w /workspace \
  prudentia-python-pytest:0.1 \
  pytest tests/visible tests/hidden \
    --json-report --json-report-file=/results/result.json
```

The exact command may change during implementation to allow writing pytest output to a mounted results directory. The invariant is fixed: no network, no host writes except the explicit run result directory, and no execution outside the ephemeral run copy.

### 10.2 Run directory

```text
.prudentia/runs/<run-id>/
  workspace-copy/
  stdout.txt
  stderr.txt
  exit_code.txt
  pytest_report.json
  run_metadata.json
```

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
| FR-001 | Local startup | prudentia doctor verifies Node, Codex availability, Docker availability, and Python runner image status. |
| FR-002 | Workspace creation | Create deterministic workspace folders, prudentia.yaml, .codex/config.toml, and initial .prudentia state. |
| FR-003 | Course profile | Capture course name, level, audience, topic, difficulty, constraints, and learning objectives. |
| FR-004 | Codex readiness | Check local Codex availability through a dry-run or adapter readiness call; never inspect credentials directly. |
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
| NFR-007 | Maintainability | Core, Codex adapter, runner, validators, and exporters are separate packages. |
| NFR-008 | Extensibility | Language/test framework support is adapter-based; MVP ships only Python/pytest adapter. |
| NFR-009 | Accessibility | Web UI supports keyboard navigation, semantic labels, plain status text, and readable error messages. |
| NFR-010 | Performance | Workspace creation under 5 seconds; export under 10 seconds for MVP-size projects; AI time excluded. |
| NFR-011 | Transparency | UI displays that Codex/OpenAI usage is controlled by the teacher-managed local Codex setup. |
| NFR-012 | Security logging | Logs include workflow events and approval decisions but redact secrets and personal data patterns. |

## 14. Prompt and context contracts

Prudentia should use stable prompt templates. Prompt text is versioned in packages/generators/prompts. Each prompt begins with a product-specific control block and includes the context manifest path.

### 14.1 Global task instruction

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

### 14.2 Context manifest schema

```ts
export interface ContextManifest {
  schemaVersion: '0.1';
  manifestId: string;
  workspaceId: string;
  taskKind: CodexTaskKind;
  createdAt: string;
  includedFiles: Array<{
    path: string;
    reason: string;
    role: 'student_visible' | 'teacher_only' | 'metadata' | 'test' | 'report';
  }>;
  excludedGlobs: string[];
  allowedWriteGlobs: string[];
  privacyWarnings: string[];
}
```

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

## 16. Security and privacy implementation requirements

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
Node.js 20+ is installed

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
- All packages have automated tests for core schemas, export scanner, and workspace creation.
- At least one example assignment exists in examples/.
- README has installation, Codex setup, Docker setup, and demo instructions.
- SECURITY.md documents local execution risks and how to report issues.

## 18. Implementation milestones

| Milestone | Deliverable | Exit criteria |
| --- | --- | --- |
| M1: Repo and schemas | Monorepo, core domain models, prudentia.yaml parser, workspace creation. | prudentia create produces valid folder and metadata. |
| M2: Codex adapter | @openai/codex-sdk integration, readiness check, one task execution. | Codex can write a brief.md into workspace. |
| M3: Generation pipeline | Generate brief, starter, solution, tests, rubric. | Generate All creates required artifacts. |
| M4: Docker runner | Python/pytest sandbox runner and validation reports. | Reference solution can be tested in container. |
| M5: Simulation and repair | Simulated submissions and bounded repair loop. | Simulation matrix is generated. |
| M6: Export scanner | Student and teacher ZIP packages with manifests. | Forbidden-file tests pass. |
| M7: Local web UI | Guided UI for all MVP workflows. | Demo can be completed without CLI except app launch. |
| M8: Open-source polish | README, docs, tests, examples, SECURITY.md. | External developer can run demo from docs. |

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
| Codex SDK/API changes. | Keep Codex integration isolated in codex-adapter package with integration tests. |
| Privacy concerns. | No cloud in MVP; context preview; no real student grading. |

## 22. Source basis

The following external assumptions are based on official OpenAI developer documentation accessed on 2 May 2026:

- Codex SDK documentation: programmatically control local Codex agents; TypeScript SDK uses @openai/codex-sdk and requires server-side Node.js 18 or later. https://developers.openai.com/codex/sdk
- Codex CLI documentation: local Codex can read, change, and run code on the user machine in the selected directory; CLI setup uses local authentication. https://developers.openai.com/codex/cli
- Codex authentication documentation: Codex supports ChatGPT sign-in for subscription access and API-key sign-in for usage-based access; API-key use is billed through the OpenAI Platform. https://developers.openai.com/codex/auth
- Codex agent approvals and security documentation: local Codex uses sandbox and approval controls; defaults include no network access and write permissions limited to the active workspace. https://developers.openai.com/codex/agent-approvals-security
- Codex configuration reference: sandbox_mode and sandbox_workspace_write configuration keys. https://developers.openai.com/codex/config-reference
