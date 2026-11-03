"""Measured AI workflow lifetime, excluding pauses for human approvals."""

from datetime import datetime

from app.domains.benchmark.schemas.benchmark_observation import BenchmarkObservation


def active_workflow_duration_ms(
    task_created_at: datetime,
    response_created_at: datetime,
    observations: BenchmarkObservation,
) -> tuple[int | None, int | None]:
    """Measure elapsed Task-to-final-response time minus merged approval waits.

    Includes Planner, Network and Analyst workflows plus orchestration overhead,
    but not pre-task GNS3 fault preparation or idle approval waiting. This is
    not a claim about model-only inference time. Reject incomplete/invalid
    waiting evidence rather than invent a duration.
    """
    if observations.approval_wait_open:
        return None, None
    try:
        total = (response_created_at - task_created_at).total_seconds()
        if total < 0:
            return None, None
        ranges: list[tuple[datetime, datetime]] = []
        for pause in observations.approval_wait_intervals:
            if pause.resumed_at < pause.started_at:
                return None, None
            if pause.started_at < task_created_at or pause.resumed_at > response_created_at:
                return None, None
            ranges.append((pause.started_at, pause.resumed_at))
        ranges.sort()
        merged: list[tuple[datetime, datetime]] = []
        for start, end in ranges:
            if merged and start <= merged[-1][1]:
                previous_start, previous_end = merged[-1]
                merged[-1] = previous_start, max(previous_end, end)
            else:
                merged.append((start, end))
        wait = sum((end - start).total_seconds() for start, end in merged)
        return round((total - wait) * 1000), round(wait * 1000)
    except (TypeError, OverflowError):
        return None, None
