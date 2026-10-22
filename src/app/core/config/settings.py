"""Validated application settings loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Shared infrastructure configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # Application/API settings được gom riêng để `.env` dễ quan sát.
    app_name: str = "Multi-Agent AI Network Automation Platform"
    app_env: Literal["development", "test", "production"] = "development"
    app_debug: bool = False
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = Field(default=8000, gt=0, le=65535)
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # PostgreSQL URL được Docker Compose override thành hostname `db`.
    database_url: str = (
        "postgresql://network_automation_user:network_dev_password@localhost:5432/"
        "network_automation_db"
    )
    # Chỉ backend dùng khóa này để giải mã credential khi mở kết nối Netmiko.
    device_credential_encryption_key: str = ""
    # Khóa ký access token identity, độc lập với khóa credential thiết bị.
    auth_jwt_secret: str = "development-only-change-me"
    auth_access_token_minutes: int = Field(default=15, gt=0, le=1440)
    auth_refresh_token_days: int = Field(default=30, gt=0, le=365)

    # GNS3 project settings.
    gns3_ip: str = "127.0.0.1"
    gns3_port: int = Field(default=3080, gt=0, le=65535)
    gns3_project_id: str = Field(
        default="",
        validation_alias=AliasChoices("GNS3_PROJECT_ID", "PROJECT_ID"),
    )
    gns3_request_timeout: float = Field(default=10.0, gt=0)

    # Network connection timeouts.
    ssh_timeout: int = Field(default=60, gt=0)
    ssh_auth_timeout: int = Field(default=30, gt=0)
    ssh_delay_factor: float = Field(default=0.5, gt=0)
    network_backend: Literal["netmiko", "nornir"] = "netmiko"
    nornir_num_workers: int = Field(default=20, gt=0, le=200)

    # AI provider settings.
    nvidia_api_key: str = ""
    nvidia_model: str = ""
    conversation_title_timeout_seconds: float = Field(default=10.0, gt=0, le=60)

    @property
    def gns3_base_url(self) -> str:
        """Canonical URL của GNS3 Controller API."""

        return f"http://{self.gns3_ip}:{self.gns3_port}/v2"

    @property
    def gns3_project_url(self) -> str:
        """Canonical URL của GNS3 project đã cấu hình."""

        return f"{self.gns3_base_url}/projects/{self.gns3_project_id}"

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse comma-separated browser origins into an explicit allowlist."""

        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    """Return one validated settings instance per process."""
    return Settings()
