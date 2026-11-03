"""One pool per database URL, fresh Session per transaction, clean disposal."""

from app.core.database import create_session_factory, dispose_session_factories


def test_factories_are_shared_for_canonical_database_url(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'shared.sqlite3'}"
    try:
        first = create_session_factory(database_url)
        second = create_session_factory(database_url)
        assert first is second
        assert first.kw["bind"] is second.kw["bind"]
        with first() as session_a, second() as session_b:
            assert session_a is not session_b
    finally:
        dispose_session_factories()


def test_disposing_factories_releases_engine_and_allows_recreation(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'disposed.sqlite3'}"
    try:
        first = create_session_factory(database_url)
        first_engine = first.kw["bind"]
        dispose_session_factories()
        second = create_session_factory(database_url)
        assert second is not first
        assert second.kw["bind"] is not first_engine
    finally:
        dispose_session_factories()
