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


def test_distinct_repositories_reuse_the_same_process_pool(tmp_path):
    from app.domains.identity.repositories.role import RoleRepository
    from app.domains.inventory.repositories.device import DeviceRepository

    database_url = f"sqlite:///{tmp_path / 'repos.sqlite3'}"
    try:
        roles = RoleRepository(database_url)
        devices = DeviceRepository(database_url)
        assert roles._sessions is devices._sessions
        assert roles._sessions.kw["bind"] is devices._sessions.kw["bind"]
    finally:
        dispose_session_factories()


def test_lifespan_disposal_reuses_factory_for_cached_services(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'restarted.sqlite3'}"
    try:
        service_factory = create_session_factory(database_url)
        dispose_session_factories(clear_registry=False)
        next_lifespan_factory = create_session_factory(database_url)
        assert next_lifespan_factory is service_factory
        # The previously disposed Engine can establish new connections on demand.
        with next_lifespan_factory() as session:
            assert session.execute(__import__("sqlalchemy").text("SELECT 1")).scalar() == 1
    finally:
        dispose_session_factories()
