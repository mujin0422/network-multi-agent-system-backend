"""SQLAlchemy engine and session factory shared by the application process."""

from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


_engines: set[Engine] = set()


@lru_cache
def _create_engine(database_url: str) -> Engine:
    """Tạo duy nhất một connection pool cho mỗi database URL trong tiến trình."""

    settings = get_settings()
    sqlalchemy_url = database_url.replace(
        "postgresql://",
        "postgresql+psycopg://",
        1,
    )
    engine_options: dict[str, object] = {"pool_pre_ping": True}
    if sqlalchemy_url.startswith("postgresql+"):
        engine_options.update(
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_timeout=settings.db_pool_timeout_seconds,
            pool_recycle=settings.db_pool_recycle_seconds,
        )
    engine = create_engine(sqlalchemy_url, **engine_options)
    _engines.add(engine)
    return engine


@lru_cache
def create_session_factory(database_url: str) -> sessionmaker[Session]:
    """Dùng chung engine/pool nhưng tạo Session độc lập cho mỗi thao tác."""

    return sessionmaker(bind=_create_engine(database_url), expire_on_commit=False)


def dispose_database_engines() -> None:
    """Đóng toàn bộ connection pool khi tiến trình ứng dụng kết thúc."""

    for engine in tuple(_engines):
        engine.dispose()
    _engines.clear()
    create_session_factory.cache_clear()
    _create_engine.cache_clear()
