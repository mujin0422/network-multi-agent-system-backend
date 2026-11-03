"""Task Success Rate over all benchmark runs, including abnormal outcomes."""

import pytest

from app.domains.benchmark.utils.summary import classify_run, summarize_run_groups


@pytest.mark.parametrize(
    "status,has_source,has_evaluation,goal,has_error,expected",
    [
        ("COMPLETED", True, True, "PASS", False, "passed"),
        ("CLEANED", True, True, "PASS", False, "passed"),
        ("COMPLETED", True, True, "FAIL", False, "failed"),
        ("CLEANED", True, True, "FAIL", False, "failed"),
        ("FAILED", True, False, None, True, "failed"),
        ("FAILED", False, False, None, True, "setup_failed"),
        ("CLEANED", False, False, None, True, "setup_failed"),
        ("CLEANED", True, False, None, True, "failed"),
        ("CLEANED", True, False, None, False, "unscored"),
        ("COMPLETED", True, True, None, False, "unscored"),
        ("COMPLETED", True, True, "UNKNOWN", False, "unscored"),
        ("PREPARING", False, False, None, False, "not_started"),
        ("READY", False, False, None, False, "not_started"),
        ("CLEANED", False, False, None, False, "not_started"),
        ("RUNNING", True, False, None, False, "in_progress"),
    ],
)
def test_tsr_run_outcome_classification(
    status, has_source, has_evaluation, goal, has_error, expected,
) -> None:
    assert classify_run(status, has_source, has_evaluation, goal, has_error) == expected


def test_tsr_uses_full_counts_and_excludes_unfinished_from_denominator() -> None:
    summary = summarize_run_groups([
        ("COMPLETED", True, True, "PASS", False, 4),
        ("CLEANED", True, True, "PASS", False, 2),
        ("CLEANED", True, True, "FAIL", False, 1),
        ("FAILED", True, False, None, True, 1),
        ("FAILED", False, False, None, True, 3),
        ("RUNNING", True, False, None, False, 5),
        ("READY", False, False, None, False, 2),
        ("CLEANED", True, False, None, False, 1),
    ])
    assert summary.total_runs == 19
    assert summary.passed == 6
    assert summary.failed == 2
    assert summary.eligible_runs == 8
    assert summary.success_rate == 75.0
    assert summary.setup_failed == 3
    assert summary.in_progress == 5
    assert summary.not_started == 2
    assert summary.unscored == 1


def test_tsr_not_defined_with_zero_scored_attempts() -> None:
    summary = summarize_run_groups([
        ("READY", False, False, None, False, 20),
        ("RUNNING", True, False, None, False, 7),
    ])
    assert summary.total_runs == 27
    assert summary.eligible_runs == 0
    assert summary.success_rate is None


def test_tsr_empty_database_is_not_zero_percent() -> None:
    summary = summarize_run_groups([])
    assert summary.total_runs == 0
    assert summary.success_rate is None
