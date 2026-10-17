"""Static checks for the versioned SQL migration chain."""

from scripts import migrate


def test_initial_migration_is_the_only_project_baseline() -> None:
    migrations = migrate.load_migrations()

    assert [item.version for item in migrations] == ["0001"]
    assert migrations[0].name == "initial_schema"
    assert migrations[0].sql.startswith(migrate.CANONICAL_SCHEMA_DIRECTIVE)
    assert all(len(item.checksum) == 64 for item in migrations)


def test_canonical_schema_is_safe_for_transactional_bootstrap() -> None:
    schema = migrate.canonical_schema_sql()

    assert "\\set ON_ERROR_STOP" not in schema
    assert "\nBEGIN;\n" not in schema
    assert not schema.rstrip().endswith("COMMIT;")
    assert "CREATE TABLE task_evaluations" in schema


def test_initial_migration_resolves_to_canonical_schema() -> None:
    migration = migrate.load_migrations()[0]

    assert migrate.executable_sql(migration) == migrate.canonical_schema_sql()
