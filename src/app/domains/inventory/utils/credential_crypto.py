"""SQL expression helpers cho mã hóa credential bằng PostgreSQL pgcrypto."""

from typing import Any

from sqlalchemy import func


def encrypted_credential(value: str, encryption_key: str) -> Any:
    """Tạo SQL expression mã hóa AES-256 và armor ciphertext trước khi lưu."""

    return func.armor(
        func.pgp_sym_encrypt(
            value,
            encryption_key,
            "cipher-algo=aes256,compress-algo=1",
        )
    )
