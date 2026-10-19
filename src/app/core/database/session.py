"""SQLAlchemy engine and session factory configuration."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def create_session_factory(database_url: str) -> sessionmaker[Session]:
    """Create a synchronous PostgreSQL session factory using psycopg 3."""

    sqlalchemy_url = database_url.replace(
        "postgresql://",
        "postgresql+psycopg://",
        1,
    )
    engine = create_engine(sqlalchemy_url, pool_pre_ping=True)
    return sessionmaker(bind=engine, expire_on_commit=False)
