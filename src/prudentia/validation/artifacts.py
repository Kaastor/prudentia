from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, Field

from prudentia.workspace.manager import Workspace, load_workspace


class ValidationIssue(BaseModel):
    code: str
    path: str | None = None
    message: str
    severity: str = "error"


class ArtifactValidationResult(BaseModel):
    ok: bool
    issues: list[ValidationIssue] = Field(default_factory=list)


REQUIRED_FILES = [
    "prudentia.yaml",
    "brief.md",
    "README.student.md",
    "pyproject.toml",
    "starter/src/assignment.py",
    "solution/src/assignment.py",
    "tests/visible/test_basic.py",
    "tests/hidden/test_edge_cases.py",
    "rubric.md",
]

STUDENT_STARTER_FORBIDDEN = [
    "return normalized == normalized[::-1]",
    "REFERENCE SOLUTION",
]

BRIEF_KEYWORDS = [
    "learning objectives",
    "task description",
    "input and output",
    "constraints",
    "submission instructions",
]

RUBRIC_KEYWORDS = ["criteria", "points", "common mistakes"]


def read_text(workspace: Workspace, relative_path: str) -> str:
    path = workspace.path(relative_path)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def count_pytest_tests(source: str) -> int:
    return len(re.findall(r"^\s*def\s+test_[A-Za-z0-9_]+\s*\(", source, flags=re.MULTILINE))


def validate_artifacts(root: Path | str) -> ArtifactValidationResult:
    workspace = load_workspace(root)
    issues: list[ValidationIssue] = []
    for required in REQUIRED_FILES:
        path = workspace.path(required)
        if not path.exists():
            issues.append(ValidationIssue(code="missing_required_file", path=required, message=f"Required file is missing: {required}"))

    brief = read_text(workspace, "brief.md").lower()
    for keyword in BRIEF_KEYWORDS:
        if keyword not in brief:
            issues.append(ValidationIssue(code="brief_missing_section", path="brief.md", message=f"brief.md should include {keyword}."))

    starter = read_text(workspace, "starter/src/assignment.py")
    for marker in STUDENT_STARTER_FORBIDDEN:
        if marker in starter:
            issues.append(
                ValidationIssue(
                    code="starter_solution_leak",
                    path="starter/src/assignment.py",
                    message=f"Starter contains forbidden solution marker: {marker}",
                )
            )
    if "NotImplementedError" not in starter and "TODO" not in starter:
        issues.append(
            ValidationIssue(
                code="starter_not_skeletal",
                path="starter/src/assignment.py",
                message="Starter should clearly leave implementation work for students.",
            )
        )

    visible = read_text(workspace, "tests/visible/test_basic.py")
    if count_pytest_tests(visible) < 3:
        issues.append(
            ValidationIssue(
                code="too_few_visible_tests",
                path="tests/visible/test_basic.py",
                message="Visible tests should contain at least three pytest tests.",
            )
        )

    hidden = read_text(workspace, "tests/hidden/test_edge_cases.py")
    if count_pytest_tests(hidden) < 3:
        issues.append(
            ValidationIssue(
                code="too_few_hidden_tests",
                path="tests/hidden/test_edge_cases.py",
                message="Hidden tests should contain at least three pytest tests.",
            )
        )

    rubric = read_text(workspace, "rubric.md").lower()
    for keyword in RUBRIC_KEYWORDS:
        if keyword not in rubric:
            issues.append(ValidationIssue(code="rubric_missing_content", path="rubric.md", message=f"rubric.md should include {keyword}."))

    return ArtifactValidationResult(ok=not issues, issues=issues)
