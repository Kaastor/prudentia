from __future__ import annotations

from prudentia.core.models import TaskKind, WorkspaceMetadata

CONTROL_BLOCK = """You are the Codex worker for Prudentia, a local-first CS assignment studio.
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
"""

PROMPT_VERSION = "0.1"


def build_prompt(task_kind: TaskKind, metadata: WorkspaceMetadata, manifest_path: str) -> str:
    task_goal = {
        TaskKind.PLANNING: "Create a concise implementation plan for the assignment artifacts.",
        TaskKind.BRIEF: "Generate or revise brief.md and README.student.md for the assignment.",
        TaskKind.STARTER: "Generate starter/src/assignment.py without including the reference solution.",
        TaskKind.SOLUTION: "Generate solution/src/assignment.py as the teacher-only reference implementation.",
        TaskKind.TESTS: "Generate visible and hidden pytest tests with normal and edge cases.",
        TaskKind.REPAIR: "Repair only solution and tests using the validation report as evidence.",
        TaskKind.RUBRIC: "Generate rubric.md with point values, criteria, and common mistakes.",
        TaskKind.SIMULATIONS: "Generate weak, partial, and misconception simulated submissions.",
        TaskKind.REPORT: "Generate teacher-facing reports from validation and simulation outputs.",
        TaskKind.QUALITY_REVIEW: "Review generated artifacts and report unresolved issues without broad rewrites.",
    }[task_kind]
    objectives = "\n".join(f"- {objective}" for objective in metadata.assignment.learning_objectives)
    constraints = (
        "\n".join(f"- {constraint}" for constraint in metadata.assignment.constraints) or "- Keep the assignment beginner-friendly."
    )
    return f"""{CONTROL_BLOCK}
Prompt version: {PROMPT_VERSION}
Task kind: {task_kind.value}
Context manifest: {manifest_path}

Assignment:
- Title: {metadata.title}
- Course: {metadata.course.name}
- Topic: {metadata.assignment.topic}
- Difficulty: {metadata.assignment.difficulty}
- Estimated minutes: {metadata.assignment.estimated_minutes}

Learning objectives:
{objectives}

Teacher constraints:
{constraints}

Goal:
{task_goal}
"""
