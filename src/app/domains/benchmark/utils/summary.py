"""Classify each run independently of cleanup or API list pagination."""

from app.domains.benchmark.schemas.benchmark_run_summary import BenchmarkRunSummary


def classify_run(
    status: str,
    has_source_message: bool,
    has_evaluation: bool,
    goal_result: str | None,
    has_error: bool,
) -> str:
    """Group completed AI attempts by GOAL, never use RCA as a TSR proxy."""
    if status in {"PREPARING", "READY"}:
        return "not_started"
    if status == "RUNNING":
        return "in_progress"
    if status == "FAILED":
        return "failed" if has_source_message else "setup_failed"
    if status in {"COMPLETED", "CLEANED"}:
        if has_evaluation and goal_result == "PASS":
            return "passed"
        if has_evaluation and goal_result == "FAIL":
            return "failed"
        if has_source_message:
            return "failed" if has_error else "unscored"
        return "setup_failed" if has_error else "not_started"
    return "unscored"


def summarize_run_groups(
    groups: list[tuple[str, bool, bool, str | None, bool, int]],
) -> BenchmarkRunSummary:
    """Aggregate SQL grouped counts across all runs (not a 100-row sample)."""
    counts = {key: 0 for key in (
        "passed", "failed", "in_progress", "not_started", "setup_failed", "unscored",
    )}
    for status, has_source, has_evaluation, goal, has_error, count in groups:
        category = classify_run(status, has_source, has_evaluation, goal, has_error)
        counts[category] += count
    eligible = counts["passed"] + counts["failed"]
    return BenchmarkRunSummary(
        **counts,
        total_runs=sum(counts.values()),
        eligible_runs=eligible,
        success_rate=round(counts["passed"] / eligible * 100, 2) if eligible else None,
    )
