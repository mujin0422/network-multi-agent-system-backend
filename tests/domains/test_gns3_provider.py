"""Kiểm thử availability check mà không gọi GNS3 thật."""

from app.core.config import Settings
from app.domains.inventory.providers import GNS3Provider


def test_provider_only_checks_gns3_version_endpoint(monkeypatch) -> None:
    settings = Settings(gns3_ip="192.0.2.10", gns3_port=3080, _env_file=None)
    provider = GNS3Provider(settings)
    requested_urls: list[str] = []

    def fake_request(url: str):
        requested_urls.append(url)
        return {"version": "2.2.54"}

    monkeypatch.setattr(provider, "_request", fake_request)

    assert provider.check_server_available() == {"version": "2.2.54"}
    assert requested_urls == ["http://192.0.2.10:3080/v2/version"]


def test_legacy_project_id_environment_name_is_still_supported() -> None:
    settings = Settings(PROJECT_ID="legacy-project", _env_file=None)

    assert settings.gns3_project_id == "legacy-project"
    assert settings.gns3_project_url.endswith("/projects/legacy-project")
