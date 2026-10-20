"""Các hàm thuần hỗ trợ password và token của Identity domain."""

import hashlib

import bcrypt


def hash_password(password: str) -> str:
    """Tạo bcrypt hash để lưu password an toàn."""

    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    """Kiểm tra password với bcrypt hash, gồm hash pgcrypto của seed cũ."""

    try:
        encoded = password_hash.encode()
        if encoded.startswith((b"$2a$", b"$2b$", b"$2y$")):
            return bcrypt.checkpw(password.encode(), encoded)

        # Dữ liệu seed development cũ được tạo bởi PostgreSQL pgcrypto crypt().
        import crypt

        return crypt.crypt(password, password_hash) == password_hash
    except (ValueError, OSError):
        return False


def hash_refresh_token(token: str) -> str:
    """Tạo SHA-256 digest; database không lưu refresh token dạng rõ."""

    return hashlib.sha256(token.encode()).hexdigest()
