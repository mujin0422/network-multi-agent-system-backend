"""Explicit transaction boundary for short business database operations.

The Unit of Work owns commit/rollback. Repositories receive the same Session
and must never open a second transaction or commit within it.
Do not hold this context open during LLM, network, or approval waits.
"""

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy.orm import Session, sessionmaker

from app.core.database.session import create_session_factory


class DatabaseUnitOfWork:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._sessions = session_factory

    @classmethod
    def from_url(cls, database_url: str) -> "DatabaseUnitOfWork":
        return cls(create_session_factory(database_url))

    @contextmanager
    def begin(self) -> Iterator[Session]:
        with self._sessions.begin() as session:
            yield session
