from __future__ import annotations

from pathlib import Path
from typing import Any

from prudentia.core.jsonio import read_json
from prudentia.core.time import utc_now_iso
from prudentia.workspace.manager import load_workspace, log_action


def _read_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = read_json(path)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _read_optional_text(path: Path) -> str | None:
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8", errors="replace")


def refresh_reports(root: Path | str) -> Path:
    workspace = load_workspace(root)
    validation = _read_optional_json(workspace.path("reports/validation_report.json"))
    matrix_text = _read_optional_text(workspace.path("reports/simulation_matrix.md"))
    export_manifests = sorted(workspace.path(".prudentia/export_manifests").glob("*.json"))
    export_lines = []
    for manifest in export_manifests[-5:]:
        data = _read_optional_json(manifest) or {}
        export_lines.append(
            f"- {data.get('export_kind', 'export')} — {data.get('status', 'unknown')} — {data.get('zip_path', manifest.name)}"
        )
    validation_status = "not run"
    unresolved: list[str] = []
    if validation:
        validation_status = "passed" if validation.get("ok") else "failed"
        unresolved = list(validation.get("unresolved_issues") or [])
    artifact_lines = []
    for artifact in [
        "brief.md",
        "README.student.md",
        "starter/src/assignment.py",
        "solution/src/assignment.py",
        "tests/visible/test_basic.py",
        "tests/hidden/test_edge_cases.py",
        "rubric.md",
    ]:
        artifact_lines.append(f"- {artifact}: {'present' if workspace.path(artifact).exists() else 'missing'}")
    report = [
        f"# Teacher report: {workspace.metadata.title}",
        "",
        f"Generated: {utc_now_iso()}",
        "",
        "## Assignment metadata",
        f"- Course: {workspace.metadata.course.name}",
        f"- Topic: {workspace.metadata.assignment.topic}",
        f"- Difficulty: {workspace.metadata.assignment.difficulty}",
        f"- Estimated minutes: {workspace.metadata.assignment.estimated_minutes}",
        "",
        "## Validation result",
        f"- Status: {validation_status}",
        "",
        "## Generated artifacts",
        *artifact_lines,
        "",
        "## Simulation outcomes",
    ]
    if matrix_text:
        report.extend(["See `reports/simulation_matrix.md` for the full generated-submission matrix.", ""])
        summary_lines = [line for line in matrix_text.splitlines() if line.startswith("| ") and "Profile" not in line and "---" not in line]
        report.extend(summary_lines[:5] or ["Simulation matrix exists but contains no rows."])
    else:
        report.append("Simulation matrix has not been generated yet.")
    report.extend(["", "## Unresolved issues"])
    if unresolved:
        report.extend(f"- {issue}" for issue in unresolved)
    else:
        report.append("- None recorded.")
    report.extend(["", "## Export status"])
    report.extend(export_lines or ["- No exports have been built yet."])
    report.extend(
        [
            "",
            "## Safety notes",
            "- Student package generation uses an allowlist and content scanner.",
            "- Teacher package generation excludes Codex configuration and credential-like content.",
        ]
    )
    path = workspace.path("reports/teacher_report.md")
    path.write_text("\n".join(report) + "\n", encoding="utf-8")
    log_action(workspace.root, "teacher_report_refreshed", {"path": "reports/teacher_report.md"})
    return path
