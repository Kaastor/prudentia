from __future__ import annotations

from pathlib import Path

from prudentia.core.models import TaskKind
from prudentia.workspace.manager import Workspace, log_action


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def write_common_files(workspace: Workspace) -> list[str]:
    pyproject = """
[project]
name = "palindrome-assignment"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = []

[tool.pytest.ini_options]
pythonpath = ["starter/src"]
testpaths = ["tests/visible"]
"""
    write_file(workspace.path("pyproject.toml"), pyproject)
    return ["pyproject.toml"]


def write_brief(workspace: Workspace) -> list[str]:
    metadata = workspace.metadata
    objectives = "\n".join(f"- {objective}" for objective in metadata.assignment.learning_objectives)
    constraints = (
        "\n".join(f"- {constraint}" for constraint in metadata.assignment.constraints)
        or "- Use only the Python standard library.\n- Implement a pure function with no input prompts or print calls."
    )
    brief = f"""
# {metadata.title}

## Learning objectives
{objectives}

## Task description
Write a function named `is_palindrome(text: str) -> bool` in `starter/src/assignment.py`.
The function should decide whether the supplied text reads the same forward and backward after normalizing it.

## Input and output expectations
- Input: a Python string named `text`.
- Output: `True` when the normalized text is a palindrome, otherwise `False`.
- Normalization means ignoring case and ignoring non-alphanumeric characters such as spaces and punctuation.
- The empty string counts as a palindrome after normalization.

## Constraints
{constraints}

## Examples
- `is_palindrome("racecar")` returns `True`.
- `is_palindrome("Race car!")` returns `True`.
- `is_palindrome("python")` returns `False`.

## Submission instructions
Edit only `starter/src/assignment.py` unless your teacher gives different instructions.
Run the visible pytest suite before submitting your work.
"""
    readme = f"""
# Student README: {metadata.title}

This package contains the assignment brief, starter implementation, and visible tests.

## Setup
Use Python 3.12 or newer. From the package root, run:

```bash
python -m pip install pytest
python -m pytest
```

## What to edit
Implement `is_palindrome` in `starter/src/assignment.py`.
Do not rename the function, change its parameters, or add interactive input.

## Local checks
The visible tests cover normal examples and a few edge cases. Passing them is necessary but not a guarantee of full credit.
"""
    write_file(workspace.path("brief.md"), brief)
    write_file(workspace.path("README.student.md"), readme)
    changed = ["brief.md", "README.student.md"] + write_common_files(workspace)
    log_action(workspace.root, "deterministic_brief_written", {"changed_files": changed})
    return changed


def write_starter(workspace: Workspace) -> list[str]:
    starter = '''
"""Starter code for the palindrome checker assignment."""


def is_palindrome(text: str) -> bool:
    """Return whether text is a palindrome after normalization.

    Normalization should ignore case and non-alphanumeric characters.
    Replace the TODO with your implementation.
    """
    # TODO: build a normalized string that ignores case and non-alphanumeric characters.
    # TODO: compare the normalized text with its reverse and return a boolean.
    raise NotImplementedError("Implement is_palindrome")
'''
    write_file(workspace.path("starter/src/assignment.py"), starter)
    log_action(workspace.root, "deterministic_starter_written", {"changed_files": ["starter/src/assignment.py"]})
    return ["starter/src/assignment.py"]


def write_solution(workspace: Workspace) -> list[str]:
    solution = '''
"""Teacher-only implementation for the palindrome checker assignment."""


def is_palindrome(text: str) -> bool:
    """Return whether text is a palindrome after ignoring case and punctuation."""
    normalized = "".join(character.lower() for character in text if character.isalnum())
    return normalized == normalized[::-1]
'''
    write_file(workspace.path("solution/src/assignment.py"), solution)
    log_action(workspace.root, "deterministic_solution_written", {"changed_files": ["solution/src/assignment.py"]})
    return ["solution/src/assignment.py"]


def write_tests(workspace: Workspace) -> list[str]:
    visible = """
from assignment import is_palindrome


def test_simple_palindrome_word():
    assert is_palindrome("racecar") is True


def test_simple_non_palindrome_word():
    assert is_palindrome("python") is False


def test_case_is_ignored():
    assert is_palindrome("Level") is True


def test_empty_string_is_palindrome():
    assert is_palindrome("") is True
"""
    edge = """
from assignment import is_palindrome


def test_spaces_and_punctuation_are_ignored():
    assert is_palindrome("A man, a plan, a canal: Panama!") is True


def test_digits_are_considered_alphanumeric():
    assert is_palindrome("12ab!!a21") is True


def test_mixed_text_that_is_not_palindrome():
    assert is_palindrome("palindrome checker") is False


def test_only_punctuation_normalizes_to_empty():
    assert is_palindrome("... !!!") is True


def test_matching_ends_are_not_enough():
    assert is_palindrome("abca") is False
"""
    write_file(workspace.path("tests/visible/test_basic.py"), visible)
    write_file(workspace.path("tests/hidden/test_edge_cases.py"), edge)
    changed = ["tests/visible/test_basic.py", "tests/hidden/test_edge_cases.py"]
    log_action(workspace.root, "deterministic_tests_written", {"changed_files": changed})
    return changed


def write_rubric(workspace: Workspace) -> list[str]:
    rubric = """
# Rubric: Palindrome checker

Total: 10 points

## Criteria
- Function signature and pure behavior: 2 points
- Correct normalization of case and non-alphanumeric characters: 3 points
- Correct palindrome decision for normal and edge cases: 3 points
- Clear, simple, readable Python code: 1 point
- Passes the visible pytest suite without special-casing tests: 1 point

## Common mistakes
- Comparing the original string without normalization.
- Ignoring case but not punctuation or spaces.
- Returning strings such as "yes" or "no" instead of booleans.
- Reading input or printing output instead of returning a value.
- Special-casing only the examples from the brief.
"""
    write_file(workspace.path("rubric.md"), rubric)
    log_action(workspace.root, "deterministic_rubric_written", {"changed_files": ["rubric.md"]})
    return ["rubric.md"]


def write_simulations(workspace: Workspace) -> list[str]:
    simulations = {
        "weak/src/assignment.py": '''
"""Weak simulated submission: returns a constant answer."""


def is_palindrome(text: str) -> bool:
    return False
''',
        "partial/src/assignment.py": '''
"""Partial simulated submission: checks raw reversed text only."""


def is_palindrome(text: str) -> bool:
    return text == text[::-1]
''',
        "misconception/src/assignment.py": '''
"""Misconception simulated submission: checks only first and last normalized characters."""


def is_palindrome(text: str) -> bool:
    normalized = "".join(character.lower() for character in text if character.isalnum())
    if not normalized:
        return True
    return normalized[0] == normalized[-1]
''',
    }
    changed: list[str] = []
    for relative, content in simulations.items():
        full_relative = f"simulations/{relative}"
        write_file(workspace.path(full_relative), content)
        changed.append(full_relative)
    log_action(workspace.root, "deterministic_simulations_written", {"changed_files": changed})
    return changed


def write_deterministic_task(workspace: Workspace, task_kind: TaskKind) -> list[str]:
    if task_kind == TaskKind.BRIEF:
        return write_brief(workspace)
    if task_kind == TaskKind.STARTER:
        return write_starter(workspace)
    if task_kind == TaskKind.SOLUTION:
        return write_solution(workspace)
    if task_kind == TaskKind.TESTS:
        return write_tests(workspace)
    if task_kind == TaskKind.RUBRIC:
        return write_rubric(workspace)
    if task_kind == TaskKind.SIMULATIONS:
        return write_simulations(workspace)
    if task_kind == TaskKind.REPORT:
        from prudentia.reporting.reports import refresh_reports

        refresh_reports(workspace.root)
        return ["reports/teacher_report.md", "reports/simulation_matrix.md"]
    if task_kind in {TaskKind.PLANNING, TaskKind.QUALITY_REVIEW, TaskKind.REPAIR}:
        return []
    raise ValueError(f"Unsupported deterministic task kind: {task_kind}")
