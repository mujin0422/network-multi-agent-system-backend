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

    def list_node_interfaces(self) -> dict[str, list[str]]:
        """Lấy tên interface thật của từng node trong topology hiện tại."""

        result = self._request(f"{self._settings.gns3_project_url}/nodes")
        if not isinstance(result, list):
            raise ExternalServiceUnavailableError(
                "GNS3 Server trả về danh sách node không hợp lệ"
            )
        return {
            str(node["name"]): [
                str(port["name"])
                for port in node.get("ports", [])
                if isinstance(port, dict) and port.get("name")
            ]
            for node in result
            if isinstance(node, dict) and node.get("name")
        }

    def list_topology_neighbors(self) -> dict[str, list[dict[str, str]]]:
        """Lấy quan hệ láng giềng một hop cùng interface từ topology GNS3."""

        nodes = self._request(f"{self._settings.gns3_project_url}/nodes")
        links = self._request(f"{self._settings.gns3_project_url}/links")
        if not isinstance(nodes, list) or not isinstance(links, list):
            raise ExternalServiceUnavailableError("GNS3 topology không hợp lệ")

        node_names = {
            str(node.get("node_id")): str(node.get("name"))
            for node in nodes
            if isinstance(node, dict) and node.get("node_id") and node.get("name")
        }
        port_names = {
            (
                str(node.get("node_id")),
                int(port.get("adapter_number", -1)),
                int(port.get("port_number", -1)),
            ): str(port.get("name"))
            for node in nodes
            if isinstance(node, dict)
            for port in node.get("ports", [])
            if isinstance(port, dict) and port.get("name")
        }
        neighbors: dict[str, list[dict[str, str]]] = {
            name: [] for name in node_names.values()
        }
        for link in links:
            endpoints = link.get("nodes", []) if isinstance(link, dict) else []
            if len(endpoints) != 2:
                continue
            left, right = endpoints
            for local, peer in ((left, right), (right, left)):
                local_id = str(local.get("node_id"))
                peer_id = str(peer.get("node_id"))
                if local_id not in node_names or peer_id not in node_names:
                    continue
                key = (
                    local_id,
                    int(local.get("adapter_number", -1)),
                    int(local.get("port_number", -1)),
                )
                peer_key = (
                    peer_id,
                    int(peer.get("adapter_number", -1)),
                    int(peer.get("port_number", -1)),
                )
                neighbors[node_names[local_id]].append(
                    {
                        "device": node_names[peer_id],
                        "local_interface": port_names.get(key, "unknown"),
                        "peer_interface": port_names.get(peer_key, "unknown"),
                    }
                )
        return neighbors

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
