# Reconcile Docker-bootstrapped PostgreSQL migration history safely

## Why this exists

The existing `docker/postgres/init/01_schema.sql` is a **fully materialized
schema**: it already defines audit logs, benchmark tables, normalized task
evaluation metrics and standardized benchmark keys. But the versioned migration
runner records `0001` and `0002` separately, so an older initialized volume
may show `0003–0007 PENDING`. Replaying migration `0003` then fails at
`CREATE TYPE audit_actor_type` because that enum already exists.

The new **explicit** command validates that the *result* of `0003–0006`
exists before inserting only the corresponding tracking rows into
`schema_migrations`. It does not delete data, drop types, or rerun historical
schema-changing SQL.

## Recommended sequence for existing installations

**Back up the database before reconciling migration history.** Verify the
application is stopped or idle (no concurrent schema migration).

1. Pull the backend change and rebuild the `migrate` image:

```bash
docker compose up -d db
docker compose build migrate
```

2. **Read-only** validation — no database modification:

```bash
docker compose run --rm migrate python -m scripts.reconcile_bootstrap --check
```

Expected: `Schema 0003-0006 đủ các kiểm tra. Chưa thay đổi database.`
If it reports missing objects or constraints, **stop**; do not force insert
versions or rerun CREATE TABLE. Repair the discrepancy first.

3. After reviewing successful checks, explicitly synchronize the history:

```bash
docker compose run --rm migrate python -m scripts.reconcile_bootstrap --apply
```

This adds **only missing rows** 0003, 0004, 0005, 0006 to
`schema_migrations`, using each migration's original name/checksum and
`execution_ms = 0` to indicate it was recognized rather than re-executed.
It verifies checksums for previously applied versions and uses the same
PostgreSQL advisory lock as `scripts/migrate.py`.

4. Apply any remaining migration, including `0007`:

```bash
docker compose run --rm migrate
docker compose run --rm migrate python scripts/migrate.py --status
```

The expected result is `APPLIED` for 0001–0007. Migration 0007 uses
`ALTER TYPE ... ADD VALUE IF NOT EXISTS`; it is safe even if the two
quantitative enum labels were already added manually.

5. Verify the enum using a read-only query:

```bash
docker compose exec db sh -c \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c \
  "SELECT unnest(enum_range(NULL::evaluation_metric_type));"'
```

Expected values: GOAL, RCA, REMEDIATION, SAFETY, LATENCY,
INTERACTION_TURNS.

## Important limitations

- This is **a history reconciliation for a verified, fully bootstrapped
  schema**, not a generic migration-repair tool for arbitrary half-applied
  DDL. The command refuses to write if a required object is missing.
- It checks the existence of required enums, columns, named constraints and
  indexes; it does **not** prove every expression, historic seed row or
  application-level behaviour exactly matches the old migration scripts.
- Run **--check** first. The opt-in `--apply` records only schema history,
  not a claim that the original migrations executed at their current
  `applied_at` time.
- There is no need to reset Docker volumes or repeat benchmark seed imports.
- Future schema migrations should work against the reconciled tracking table.
