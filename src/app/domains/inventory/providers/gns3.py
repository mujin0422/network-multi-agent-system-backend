"""GNS3 Controller availability provider."""

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import Settings
from app.core.exceptions import ExternalServiceUnavailableError


class GNS3Provider:
    """Chỉ kiểm tra GNS3 Server có đang hoạt động hay không."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def check_server_available(self) -> dict[str, Any]:
        """Gọi version endpoint và báo 503 nếu GNS3 không sẵn sàng."""

        result = self._request(f"{self._settings.gns3_base_url}/version")
        if not isinstance(result, dict):
            raise ExternalServiceUnavailableError(
                "GNS3 Server trả về dữ liệu không hợp lệ"
            )
        return result

    def _request(self, url: str) -> Any:
        request = Request(url, method="GET")
        try:
            with urlopen(
                request,
                timeout=self._settings.gns3_request_timeout,
            ) as response:
                payload = response.read()
                return json.loads(payload) if payload else {}
        except HTTPError as exc:
            raise ExternalServiceUnavailableError(
                f"GNS3 Server trả HTTP {exc.code}"
            ) from exc
        except (URLError, TimeoutError) as exc:
            raise ExternalServiceUnavailableError(
                f"GNS3 Server chưa được bật hoặc không thể truy cập: {exc}"
            ) from exc
