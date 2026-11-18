from app.core.database.session import (
    create_session_factory,
    dispose_database_engines,
)


def test_session_factory_is_reused_for_the_same_database_url() -> None:
    database_url = "sqlite+pysqlite:///:memory:"

    first = create_session_factory(database_url)
    second = create_session_factory(database_url)

    assert first is second
    assert first.kw["bind"] is second.kw["bind"]
    dispose_database_engines()


def test_dispose_clears_cached_session_factory() -> None:
    database_url = "sqlite+pysqlite:///:memory:"
    first = create_session_factory(database_url)

    dispose_database_engines()
    second = create_session_factory(database_url)

    assert second is not first
    assert second.kw["bind"] is not first.kw["bind"]
    dispose_database_engines()
