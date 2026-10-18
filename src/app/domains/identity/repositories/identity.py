"""Persistence port and PostgreSQL adapter for identity records."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.domains.identity.schemas import (
    Role,
    User,
    UserRecord,
    UserSessionRecord,
)


class IdentityRepository(Protocol):
    def get_user_by_email(self, email: str) -> UserRecord | None: ...
    def get_user(self, user_id: str) -> User | None: ...
    def get_user_with_password(self, user_id: str) -> UserRecord | None: ...
    def get_role(self, role_id: str) -> Role | None: ...
    def get_permissions(self, role_id: str) -> set[tuple[str, str]]: ...
    def save_session(self, session: UserSessionRecord) -> None: ...
    def get_session_by_hash(self, token_hash: str) -> UserSessionRecord | None: ...
    def revoke_session(self, session_id: UUID, revoked_at: datetime) -> None: ...
    def is_session_active(self, session_id: UUID) -> bool: ...
    def get_active_session(self, session_id: UUID) -> UserSessionRecord | None: ...
    def rotate_session(self, session_id: UUID, revoked_at: datetime, replacement: UserSessionRecord) -> bool: ...
    def update_login(self, user_id: str, logged_in_at: datetime) -> None: ...


class PostgresIdentityRepository:
    """PostgreSQL implementation using the canonical identity tables."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def _connect(self):
        import psycopg
        from psycopg.rows import dict_row
        return psycopg.connect(self._database_url, row_factory=dict_row)

    @staticmethod
    def _user_query(where: str) -> str:
        return f"""SELECT id, role_id, email, password_hash, full_name,
            user_status, created_at, last_updated_at, last_login_at
            FROM users WHERE {where}"""

    def get_user_by_email(self, email: str) -> UserRecord | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(self._user_query("email = %s"), (email.lower(),))
            row = cur.fetchone()
        return UserRecord.model_validate(row) if row else None

    def get_user(self, user_id: str) -> User | None:
        record = self.get_user_with_password(user_id)
        return User.model_validate(record.model_dump()) if record else None

    def get_user_with_password(self, user_id: str) -> UserRecord | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(self._user_query("id = %s"), (user_id,))
            row = cur.fetchone()
        return UserRecord.model_validate(row) if row else None

    def get_role(self, role_id: str) -> Role | None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT id, name, description, created_by, last_updated_by, created_at, last_updated_at FROM roles WHERE id = %s", (role_id,))
            row = cur.fetchone()
        return Role.model_validate(row) if row else None

    def get_permissions(self, role_id: str) -> set[tuple[str, str]]:
        query = """SELECT mf.name AS function_name, a.name AS action_name
            FROM role_permissions rp
            JOIN permissions p ON p.id = rp.permission_id
            JOIN management_functions mf ON mf.id = p.function_id
            JOIN actions a ON a.id = p.action_id
            WHERE rp.role_id = %s"""
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(query, (role_id,))
            return {(row["function_name"], row["action_name"]) for row in cur.fetchall()}

    def save_session(self, session: UserSessionRecord) -> None:
        query = """INSERT INTO user_sessions (id, user_id, refresh_token_hash, expires_at, created_at, revoked_at)
            VALUES (%(id)s, %(user_id)s, %(refresh_token_hash)s, %(expires_at)s, %(created_at)s, %(revoked_at)s)"""
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(query, self._session_params(session))

    @staticmethod
    def _session_params(session: UserSessionRecord) -> dict:
        """Include secret fields intentionally excluded from normal serialization."""
        return {
            "id": session.id,
            "user_id": session.user_id,
            "refresh_token_hash": session.refresh_token_hash,
            "expires_at": session.expires_at,
            "created_at": session.created_at,
            "revoked_at": session.revoked_at,
        }

    def get_session_by_hash(self, token_hash: str) -> UserSessionRecord | None:
        query = "SELECT id, user_id, refresh_token_hash, expires_at, created_at, revoked_at FROM user_sessions WHERE refresh_token_hash = %s"
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(query, (token_hash,))
            row = cur.fetchone()
        return UserSessionRecord.model_validate(row) if row else None

    def revoke_session(self, session_id: UUID, revoked_at: datetime) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("UPDATE user_sessions SET revoked_at = %s WHERE id = %s AND revoked_at IS NULL", (revoked_at, session_id))

    def is_session_active(self, session_id: UUID) -> bool:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1 FROM user_sessions WHERE id = %s AND revoked_at IS NULL AND expires_at > CURRENT_TIMESTAMP", (session_id,))
            return cur.fetchone() is not None

    def get_active_session(self, session_id: UUID) -> UserSessionRecord | None:
        query = "SELECT id, user_id, refresh_token_hash, expires_at, created_at, revoked_at FROM user_sessions WHERE id = %s AND revoked_at IS NULL AND expires_at > CURRENT_TIMESTAMP"
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(query, (session_id,))
            row = cur.fetchone()
        return UserSessionRecord.model_validate(row) if row else None

    def rotate_session(self, session_id: UUID, revoked_at: datetime, replacement: UserSessionRecord) -> bool:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("UPDATE user_sessions SET revoked_at = %s WHERE id = %s AND revoked_at IS NULL AND expires_at > %s", (revoked_at, session_id, revoked_at))
            if cur.rowcount != 1:
                return False
            cur.execute(
                """INSERT INTO user_sessions
                    (id, user_id, refresh_token_hash, expires_at, created_at, revoked_at)
                    VALUES (%(id)s, %(user_id)s, %(refresh_token_hash)s,
                            %(expires_at)s, %(created_at)s, %(revoked_at)s)""",
                self._session_params(replacement),
            )
        return True

    def update_login(self, user_id: str, logged_in_at: datetime) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("UPDATE users SET last_login_at = %s WHERE id = %s", (logged_in_at, user_id))
