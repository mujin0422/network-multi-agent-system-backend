# Benchmark Evaluation metrics (db-benchmark-v5)

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


## NIKA 0.2-inspired structured diagnosis scoring (db-benchmark-v5)

NIKA 0.2 uses **set-based (resource_id, fault_type) pairs**. For each level,
the primary diagnostic measures are precision, recall and F1; RCA
`*_accuracy` is a backwards-compatible **recall alias**, not a
true-negative-inclusive confusion-matrix accuracy. Its implementation is
available at:
https://github.com/sands-lab/nika/blob/main/src/nika/evaluator/scoring.py

### Agent submission (not extracted from keywords)

Analyst produces the usual Vietnamese report **and** these JSON fields:

```json
{
  "is_anomaly": true,
  "root_causes": [
    {
      "device": "P1",
      "interface": "FastEthernet0/0",
      "fault_type": "link_down"
    }
  ]
}
```

`is_anomaly` must be explicitly submitted (true/false/null);
`root_causes` must be an explicit list. The Analyst sees only observed
network CLI execution results and a **general failure-type vocabulary**,
never the incident's `ground_truth` or `evaluation_required_terms`.

### Canonical RCA taxonomy

Analyst output và benchmark ground truth dùng chung `FaultType` đóng. Alias cũ
được chuẩn hóa trước khi chấm, ví dụ `acl_block` thành `acl_traffic_block`,
`wrong_netmask` thành `wrong_subnet_mask` và `bgp_neighbor_shutdown` thành
`bgp_neighbor_admin_down`. Các lỗi cấp thiết bị như BGP neighbor shutdown,
missing OSPF network và missing default route luôn được chấm ở resource `node`;
interface triệu chứng không được tính thành một root cause khác.

Evaluator vẫn giữ precision/recall/F1 theo cặp `(resource_id, fault_type)`, nhưng
không còn tạo false negative chỉ vì Analyst dùng alias tương đương. Analyst prompt
yêu cầu tập root cause tối thiểu có bằng chứng nhằm hạn chế false positive từ
thiết bị láng giềng chỉ bị ảnh hưởng.

`AnalysisOrchestrator` persists this submission under
`task_activity_events.event_data.diagnosis_submission` in its
`ANALYSIS_COMPLETED` activity, before creating `FINAL_RESPONSE`.
The benchmark evaluation reads this persisted submission, **not the
natural-language response**, and never reconstructs predictions from GT.
When the Analyst falls back due to a model or JSON error, there is no
valid submission and RCA scores zero, not PASS.

### Resource normalization and scoring

Existing GNS3 scenario `ground_truth` requires
`device`, `fault_type`, and optional `interface`.
Both the prediction and ground truth map to pairs:

- Interface-specific: `interface/{device}/{interface}`, including Cisco
  interface names with slashes (e.g. `interface/p1/fastethernet0/0`).
- Device-level (OSPF/BGP settings without an interface): `node/{device}`.
- `fault_type` is the canonical failure ID (e.g. `link_down`,
  `ospf_area_mismatch`, `bgp_neighbor_admin_down`).

Identifiers are trimmed and case-folded, but **no substring matching or
inference from keyword presence** occurs. A device, interface or failure ID
mismatch is a different pair.

Let `P` be the set of predicted pairs and `G` the set of ground-truth pairs:

```text
TP = |P ∩ G|        FP = |P - G|        FN = |G - P|
Precision = TP / (TP + FP)
Recall    = TP / (TP + FN)
F1        = 2 * Precision * Recall / (Precision + Recall)
```

Localization uses only the set of resource IDs. Fault-type scoring uses
only the set of failure IDs. The RCA metric has
`rca_precision`, `rca_recall`, `rca_f1`,
`localization_f1`, `fault_type_f1`, detection score and
TP/FP/FN evidence. **RCA PASS** means exact equality of the predicted and
expected pair sets, not merely positive recall. **GOAL PASS** requires RCA
exact match **and** `is_anomaly == true` for these fault-injection scenarios.

Invalid/missing Analyst submissions score 0 rather than receiving a
spurious keyword-based PASS; corrupt/missing GT is an evaluator error
rather than silently receiving a prediction.

### Historical scores and comparison limitations

- Evaluations **v1/v2/v3** remain unchanged and use keyword scoring.
- Evaluations **v4** score structured diagnoses; their numeric RCA F1 is
  exposed in `GET /api/v1/evaluations` via an optional `scores` object.
- No database migration is required: the Analyst submission is saved in
  existing Task Activity JSONB; numeric scores are saved in existing
  Evaluation JSONB.
- Existing scenarios/seeds are compatible, because they already have
  `ground_truth` device/interface/fault_type.
- The existing all-runs TSR still spans historical evaluation versions;
  **do not compare or pool legacy keyword-based rates with v4 RCA results
  in a scientific report without stratifying by version**. A clean
  NIKA-inspired comparison requires rerunning the same scenario set under
  the same v4 evaluator.
- Unlike NIKA's full platform, this implementation keeps the project's
  existing GNS3 topology and Agent orchestration and does **not** reproduce
  NIKA's Kathará/Containerlab environments, official benchmark cases,
  release-level scoring or agent extraction callbacks. It ports the
  structured diagnosis *scoring method*, not the entire NIKA system.

### Verification

After merging backend/frontend code, rebuild the API and run a fresh
Benchmark Scenario. Verify:

1. `ANALYSIS_COMPLETED` has a JSON `diagnosis_submission`.
2. The saved Evaluation is `db-benchmark-v5`.
3. RCA includes `rca_f1`, `localization_f1`, `fault_type_f1`,
   and FP/FN evidence; GOAL is based on detection + exact pairs.
4. The frontend displays old runs as historical keyword rubric and new
   runs with v4 RCA scores.
5. Run `pytest tests/domains/test_nika_style_rca.py tests/domains/test_benchmark_observations.py tests/domains/test_benchmark_service.py tests/agents/test_analyst_agent.py`.

NVIDIA NIM model responses may require additional JSON retries. This change
does not benchmark the model's ability to generate structured diagnoses; run
a representative GNS3 scenario for end-to-end verification.
