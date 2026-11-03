# Benchmark Evaluation metrics (db-benchmark-v3)

## AI workflow active time (LATENCY)

New v3 benchmark evaluations record **AI workflow lifetime**, not the old
end-to-end user-message latency. A run first creates a Task after the GNS3
benchmark environment is prepared. The workflow covers Planner → Network Agent
→ Analyst and the supporting orchestration and database operations.

**Definition:**

```text
active_duration_ms =
  FINAL_RESPONSE.created_at - Task.created_at
  - merged waiting intervals from APPROVAL_REQUESTED to next EXECUTION_STARTED
```

This includes AI workflow runtime, tool calls, planning and analysis, but
**excludes idle human approval waits** and GNS3 fault preparation, injection
and cleanup. It is **not model-only inference time**.

The wait interval ends on the next `EXECUTION_STARTED` recorded by the
orchestrator (not merely when the approval button is clicked). Adjacent or
overlapping waits are unioned; invalid or unfinished wait evidence produces a
**missing** measurement instead of an unjustified zero.

Detailed metric `LATENCY` now has
`actual_value={"active_duration_ms": ...}` and evidence including
`task_created_at`, `final_response_created_at`, `approval_wait_ms`,
`approval_pause_count`, and the measurement definition.

**Legacy preservation:** `db-benchmark-v2` evaluations keep their original
`LATENCY.actual_value.duration_ms` meaning
(`FINAL_RESPONSE.created_at - USER_REQUEST.created_at`, **including** approval
waits). Existing rows are **not** rewritten. The frontend shows the older
value as "legacy E2E" and **excludes it from the v3 active-runtime average**.
Both versions can still be inspected.

`INTERACTION_TURNS` is unchanged: the number of
`task_executions` records for the task with `tool_name IS NOT NULL`
(Agent→Tool invocations, not chat turns or inner reasoning steps).
Neither numerical metric has a PASS/FAIL threshold.

## Task Success Rate (TSR)

`GET /api/v1/benchmarks/runs/summary` aggregates **all Benchmark Run rows**
with a SQL GROUP BY rather than using the paginated latest 100 records.
It joins each run's Evaluation's **GOAL** metric, not the RCA metric or
run cleanup status.

```text
TSR (%) = 100 * passed / (passed + failed)
```

When no eligible runs exist the API returns `success_rate: null`, not 0%.

| Category | Meaning | In TSR denominator? |
|---|---|---|
| passed | COMPLETED/CLEANED, with GOAL PASS and saved evaluation | Yes |
| failed | COMPLETED/CLEANED with GOAL FAIL, or failed *after* an agent Chat began | Yes |
| in_progress | RUNNING | No |
| not_started | PREPARING/READY, or CLEANED before an agent Chat | No |
| setup_failed | FAILED/CLEANED on setup before the agent Chat started | No |
| unscored | Chat ran but no saved GOAL result, and no definitive execution error | No |

This classification treats a cleaned, scored run according to its original
GOAL result (cleanup must not turn a FAIL into PASS). Unscored attempts and
preparation failures are **visible separately**, not silently counted as
success. A Task that fails to produce its final answer is a failure when the
run is marked FAILED after Chat started.

The front-end displays TSR with `passed / eligible_runs` plus all six
categories and `total_runs`. GOAL is currently keyword-based (the v2/v3
rubric); thus this TSR measures the present automated rubric, **not** an
independently network-verified solution success rate.

## Deployment and verification

This version **does not change the database schema**. The prior migration
`0007` must already have added the LATENCY and INTERACTION_TURNS enum
values. Existing users who have completed `0001–0007` can deploy this
update without any migration or re-seeding.

```bash
docker compose up -d --build api
```

Then complete a **new** benchmark run and view
`/api/v1/benchmarks/runs/summary` and the Evaluation details.
Check that the new evaluation reports `db-benchmark-v3` and
`LATENCY.actual_value.active_duration_ms`. Older v2 evaluations retain
`duration_ms` and appear as legacy end-to-end in the UI.

### Still outstanding

- GOAL/RCA are keyword-based, not independent root-cause verification.
- REMEDIATION/SAFETY remain NOT_APPLICABLE.
- A run that is CLEANED after an evaluation-write exception may remain
  unscored until a separate re-evaluation workflow is developed.
