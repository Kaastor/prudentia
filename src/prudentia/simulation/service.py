from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from pydantic import BaseModel, Field

from prudentia.core.jsonio import read_json, write_json
from prudentia.core.progress import ProgressEvent, new_run_id
from prudentia.core.time import utc_now_iso
from prudentia.generation.deterministic import write_simulations
from prudentia.runner.test_runner import PytestRunResult, run_pytest
from prudentia.workspace.manager import load_workspace, record_progress

VALID_PROFILES = ["weak", "partial", "misconception"]
EXPECTED_SIGNAL = {
    "weak": "Fails most tests; detects whether tests reject constant answers.",
    "partial": "Passes raw-string cases but fails normalization requirements.",
    "misconception": "Passes superficial first/last checks but fails full palindrome logic.",
}


class SimulationRow(BaseModel):
    profile: str
    expected_signal: str
    exit_code: int
    passed: int | None = None
    failed: int | None = None
    total: int | None = None
    run_id: str
    run_dir: str
    ok: bool


class SimulationMatrix(BaseModel):
    schema_version: str = "0.1"
    workspace_id: str
    run_id: str
    created_at: str = Field(default_factory=utc_now_iso)
    rows: list[SimulationRow]


def parse_profiles(value: str | Iterable[str]) -> list[str]:
    if isinstance(value, str):
        profiles = [item.strip() for item in value.split(",") if item.strip()]
    else:
        profiles = [item.strip() for item in value if item.strip()]
    unknown = [profile for profile in profiles if profile not in VALID_PROFILES]
    if unknown:
        raise ValueError(f"Unknown simulation profiles: {', '.join(unknown)}")
    return profiles or list(VALID_PROFILES)


def summary_counts(report_path: str) -> tuple[int | None, int | None, int | None]:
    path = Path(report_path)
    if not path.exists():
        return None, None, None
    try:
        data = read_json(path)
    except Exception:
        return None, None, None
    summary: dict[str, Any] = data.get("summary", {})
    passed = summary.get("passed")
    failed = summary.get("failed")
    total = summary.get("total")
    return passed, failed, total


def write_matrix_markdown(workspace_root: Path, matrix: SimulationMatrix) -> None:
    lines = [
        "# Simulation matrix",
        "",
        "These are generated fake submissions used to evaluate assignment tests. They are not real student submissions.",
        "",
        "| Profile | Expected signal | Passed | Failed | Total | Exit code | Run ID |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in matrix.rows:
        lines.append(
            f"| {row.profile} | {row.expected_signal} | {row.passed if row.passed is not None else 'n/a'} | "
            f"{row.failed if row.failed is not None else 'n/a'} | {row.total if row.total is not None else 'n/a'} | "
            f"{row.exit_code} | `{row.run_id}` |"
        )
    (workspace_root / "reports" / "simulation_matrix.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def simulate_profiles(
    root: Path | str,
    *,
    profiles: str | Iterable[str] = "weak,partial,misconception",
    allow_native_execution: bool = False,
    prefer_docker: bool = True,
) -> SimulationMatrix:
    workspace = load_workspace(root)
    run_id = new_run_id("simulate")
    selected = parse_profiles(profiles)
    record_progress(
        workspace.root,
        ProgressEvent(
            run_id=run_id,
            workspace_id=workspace.id,
            event_kind="run_start",
            message="Simulation run started.",
            payload={"profiles": selected, "prefer_docker": prefer_docker, "allow_native_execution": allow_native_execution},
        ).model_dump(mode="json"),
    )
    write_simulations(workspace)
    rows: list[SimulationRow] = []
    for profile in selected:
        try:
            result: PytestRunResult = run_pytest(
                workspace.root,
                target=profile,  # type: ignore[arg-type]
                allow_native_execution=allow_native_execution,
                prefer_docker=prefer_docker,
            )
            passed, failed, total = summary_counts(result.pytest_report_path)
            rows.append(
                SimulationRow(
                    profile=profile,
                    expected_signal=EXPECTED_SIGNAL[profile],
                    exit_code=result.exit_code,
                    passed=passed,
                    failed=failed,
                    total=total,
                    run_id=result.run_id,
                    run_dir=result.run_dir,
                    ok=result.ok,
                )
            )
        except Exception as exc:
            rows.append(
                SimulationRow(
                    profile=profile,
                    expected_signal=EXPECTED_SIGNAL[profile],
                    exit_code=999,
                    passed=None,
                    failed=None,
                    total=None,
                    run_id="not-run",
                    run_dir="",
                    ok=False,
                )
            )
            record_progress(
                workspace.root,
                ProgressEvent(
                    run_id=run_id,
                    workspace_id=workspace.id,
                    event_kind="error",
                    message=f"Simulation profile {profile} failed to run: {exc}",
                    payload={"profile": profile},
                ).model_dump(mode="json"),
            )
    matrix = SimulationMatrix(workspace_id=workspace.id, run_id=run_id, rows=rows)
    write_json(workspace.path("reports/simulation_matrix.json"), matrix)
    write_matrix_markdown(workspace.root, matrix)
    record_progress(
        workspace.root,
        ProgressEvent(
            run_id=run_id,
            workspace_id=workspace.id,
            event_kind="validation_finish",
            message="Simulation matrix written.",
            payload=matrix.model_dump(mode="json"),
        ).model_dump(mode="json"),
    )
    return matrix
