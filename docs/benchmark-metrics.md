# Benchmark evaluation: quantitative observations (v2)

This change adds **LATENCY** and **INTERACTION_TURNS** to the existing GOAL,
RCA, REMEDIATION and SAFETY metric records. Each completed benchmark run saves
the six metrics in `task_evaluation_metrics`; the newest evaluation version is
`db-benchmark-v2`.

## Definitions

| Metric | Unit | Operational definition |
|---|---|---|
| Latency | milliseconds | `FINAL_RESPONSE.created_at − initial USER_REQUEST.created_at`, for the user message bound to the benchmark run |
| Interaction Turns | count | Number of persisted `task_executions` rows belonging to that Task where `tool_name IS NOT NULL` |

**Important semantics**

- Latency is **end-to-end Chat wall-clock time**, not inference-only model time.
  It includes tool execution, orchestration and any **human approval waiting**.
  Because the request is created after fault injection, it excludes preparation
  and injection by GNS3 Benchmark Engine. It also excludes cleanup, which
  occurs after evaluation.
- Interaction Turns here is an **Agent→Tool invocation count**. It is **not** a
  count of User↔Agent messages, internal thought steps, unique tool types, or
  retry-free logical tool actions. A repeated invocation counts as another
  turn if it has its own `task_executions` record.
- Neither quantity has a benchmark-defined success threshold. These metrics
  store `result=UNKNOWN` (not PASS or FAIL), with the number in `actual_value`.
  No impact on the pre-existing GOAL/RCA result.
- If the initial message timestamp is unavailable or chronologically later
  than the final response, Latency is missing (not 0). Counts of zero are
  valid when no tool-backed executions were recorded; this assumes tool
  execution logging is complete.
- Old evaluations are **not backfilled** or rewritten. They will have no
  Latency/Interaction Turns values until new benchmark tasks are evaluated.

## API

- `GET /api/v1/evaluations`: each summary includes a `measurements` object,
  for example `{"LATENCY": 4250, "INTERACTION_TURNS": 3}`. It is empty for
  old or non-measured evaluations.
- `GET /api/v1/evaluations/tasks/{task_id}`: detailed metrics contain
  `actual_value={"duration_ms": 4250}` for LATENCY and
  `actual_value={"count": 3}` for INTERACTION_TURNS, with provenance in `evidence`.

## Deployment

Run database migrations **before deploying/restarting the updated API**.
Migration `0007_add_benchmark_observation_metrics.sql` adds two values to the
PostgreSQL `evaluation_metric_type` enum.

```bash
docker compose up -d db
docker compose run --rm migrate
docker compose up -d --build api
```

No existing benchmark scenario seeds or GNS3 device configuration changes are
needed. Create a **new** benchmark run and complete its Chat diagnosis to
see the two new observations.

### Not yet implemented

GOAL and RCA remain keyword-based, REMEDIATION and SAFETY remain N/A for the
current diagnosis-only rubric, and TSR/RCA aggregate rates are not changed.
