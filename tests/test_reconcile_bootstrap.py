"""Safety checks for bootstrap schema history reconciliation."""

from scripts import reconcile_bootstrap


class _Result:
    def fetchone(self):
        return (True,)


class _Connection:
    def execute(self, sql, params=None):
        # Only the scenario_key NOT NULL catalog query is evaluated directly.
        assert "information_schema.columns" in sql
        return _Result()


# One intentionally broad catalog row set: all required fields of each migrated
# table are represented, while removed legacy evaluation fields are absent.
_CURRENT_FIELDS = {
    "id", "actor_user_id", "actor_display_name", "actor_type", "action",
    "resource_type", "resource_id", "event_status", "summary", "event_data",
    "request_id", "source_ip", "user_agent", "occurred_at", "scenario_key",
    "version", "name", "description", "topology", "initial_message", "definition",
    "is_active", "created_by", "last_updated_by", "created_at", "last_updated_at",
    "scenario_id", "scenario_version", "scenario_name", "scenario_snapshot",
    "status", "started_by", "conversation_id", "source_message_id", "task_id",
    "evaluation_id", "evaluation_result", "cleanup_required", "error_message",
    "started_at", "completed_at", "cleaned_at", "metric_type", "result",
    "is_required", "was_attempted", "expected_value", "actual_value", "evidence",
}


def _healthy_catalog(monkeypatch):
    monkeypatch.setattr(reconcile_bootstrap, "_present", lambda *_: True)
    monkeypatch.setattr(reconcile_bootstrap, "_columns", lambda *_: _CURRENT_FIELDS)
    monkeypatch.setattr(reconcile_bootstrap, "_constraint", lambda *_: True)
    enums = {
        "audit_actor_type": ["USER", "SYSTEM", "AGENT"],
        "audit_event_status": ["SUCCESS", "FAILED", "DENIED"],
        "evaluation_metric_type": [
            "GOAL", "RCA", "REMEDIATION", "SAFETY", "LATENCY",
            "INTERACTION_TURNS",
        ],
    }
    monkeypatch.setattr(
        reconcile_bootstrap,
        "_enum_labels",
        lambda _conn, name: enums.get(name, []),
    )


def test_complete_bootstrap_can_be_reconciled(monkeypatch) -> None:
    _healthy_catalog(monkeypatch)
    assert reconcile_bootstrap.verify_bootstrap(_Connection()) == []


def test_reconciliation_refuses_partial_audit_index(monkeypatch) -> None:
    _healthy_catalog(monkeypatch)
    monkeypatch.setattr(
        reconcile_bootstrap,
        "_present",
        lambda _conn, name: name != "idx_audit_logs_request_id",
    )
    problems = reconcile_bootstrap.verify_bootstrap(_Connection())
    assert any("idx_audit_logs_request_id" in problem for problem in problems)


def test_reconciliation_refuses_missing_benchmark_constraint(monkeypatch) -> None:
    _healthy_catalog(monkeypatch)
    monkeypatch.setattr(
        reconcile_bootstrap,
        "_constraint",
        lambda _conn, _table, name: name != "ck_benchmark_run_id_format",
    )
    problems = reconcile_bootstrap.verify_bootstrap(_Connection())
    assert any("ck_benchmark_run_id_format" in problem for problem in problems)


def test_reconciliation_refuses_old_evaluation_columns(monkeypatch) -> None:
    _healthy_catalog(monkeypatch)
    monkeypatch.setattr(
        reconcile_bootstrap,
        "_columns",
        lambda _conn, table: (
            _CURRENT_FIELDS | {"rca_result"}
            if table == "task_evaluations"
            else _CURRENT_FIELDS
        ),
    )
    problems = reconcile_bootstrap.verify_bootstrap(_Connection())
    assert any("rca_result" in problem for problem in problems)
