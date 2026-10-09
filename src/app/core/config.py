"""Validated application settings loaded from environment variables."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Shared infrastructure configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gns3_ip: str = "127.0.0.1"
    gns3_port: int = Field(default=3080, gt=0, le=65535)
    project_id: str = ""

    ssh_timeout: int = Field(default=60, gt=0)
    ssh_auth_timeout: int = Field(default=30, gt=0)
    ssh_delay_factor: float = Field(default=0.5, gt=0)

    default_device_hostname: str = "127.0.0.1"
    default_device_type: str = "cisco_ios_telnet"
    default_device_username: str = "admin"
    default_device_port: int = Field(default=23, gt=0, le=65535)
    default_device_password: str = ""

    nvidia_api_key: str = ""
    nvidia_model: str = ""


@lru_cache
def get_settings() -> Settings:
    """Return one validated settings instance per process."""
    return Settings()
