"""Process-local SQLAlchemy Engine registry and session factory.

One Engine / connection pool per canonical URL, reused by all repositories.
Session objects themselves are NEVER cached or shared across requests/tasks.
"""

from threading import RLock

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

_lock = RLock()
_factories: dict[str, sessionmaker[Session]] = {}


def _canonical_url(database_url: str) -> str:
    return database_url.replace(
        "postgresql://", "postgresql+psycopg://", 1
    )


def create_session_factory(database_url: str) -> sessionmaker[Session]:
    """Return one process-local factory/pool for the same database URL.

    The previous implementation created a separate Engine each time a
    repository was initialized. Keep sessionmaker shared, NEVER a Session.
    """
    canonical_url = _canonical_url(database_url)
    with _lock:
        factory = _factories.get(canonical_url)
        if factory is None:
            engine = create_engine(canonical_url, pool_pre_ping=True)
            factory = sessionmaker(bind=engine, expire_on_commit=False)
            _factories[canonical_url] = factory
        return factory


def dispose_session_factories() -> None:
    """Dispose every managed Engine at app shutdown (or test teardown).

    Only call after active sessions and background workers have stopped.
    """
    with _lock:
        factories = list(_factories.values())
        _factories.clear()
    for factory in factories:
        engine = factory.kw.get("bind")
        if engine is not None:
            engine.dispose()
