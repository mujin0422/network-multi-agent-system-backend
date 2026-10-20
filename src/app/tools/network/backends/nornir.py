"""Backend Nornir sử dụng plugin Netmiko để thực thi command."""

from typing import Any

from app.domains.execution.schemas import AccessMode
from app.domains.inventory.schemas import DeviceConfig
from app.domains.inventory.services import NetworkService
from app.tools.network.schemas import CommandResult


class NornirNetworkTool:
    """Tạo Nornir inventory động từ thiết bị được lưu trong database."""

    def __init__(self, network_service: NetworkService, num_workers: int = 20) -> None:
        self._network_service = network_service
        self._num_workers = num_workers

    def execute(
        self,
        device_id: str,
        access_mode: AccessMode,
        commands: list[str],
    ) -> list[CommandResult]:
        device = self._network_service.prepare_device(device_id)

        nornir = self._build_nornir(device_id, device)
        aggregated_result = nornir.run(
            task=self._run_commands,
            access_mode=access_mode,
            commands=commands,
        )
        host_result = aggregated_result[device_id]
        if host_result.failed:
            error = next(
                (str(item.exception) for item in host_result if item.exception),
                "Nornir không thể thực thi command",
            )
            raise RuntimeError(error)

        task_results = [item for item in host_result[1:] if item.result is not None]
        if access_mode == AccessMode.WRITE:
            if not task_results:
                raise RuntimeError("Nornir không trả về kết quả cấu hình")
            return [
                CommandResult(
                    command="\n".join(commands),
                    output=str(task_results[-1].result),
                )
            ]
        return [
            CommandResult(command=command, output=str(result.result))
            for command, result in zip(commands, task_results, strict=False)
        ]

    def _build_nornir(self, device_id: str, device: DeviceConfig) -> Any:
        # Import tại thời điểm sử dụng để backend Netmiko trực tiếp không phụ
        # thuộc quá trình khởi tạo plugin của Nornir.
        from nornir.core import Nornir
        from nornir.core.inventory import (
            ConnectionOptions,
            Defaults,
            Host,
            Inventory,
        )
        from nornir.plugins.runners import ThreadedRunner

        connection_options = {
            "netmiko": ConnectionOptions(
                extras={"secret": device.secret} if device.secret else {},
            )
        }
        host = Host(
            name=device_id,
            hostname=device.hostname,
            port=device.port,
            username=device.username,
            password=device.password,
            platform=device.device_type,
            connection_options=connection_options,
        )
        inventory = Inventory(
            hosts={device_id: host},
            groups={},
            defaults=Defaults(),
        )
        return Nornir(
            inventory=inventory,
            runner=ThreadedRunner(num_workers=self._num_workers),
        )

    @staticmethod
    def _run_commands(task: Any, access_mode: AccessMode, commands: list[str]) -> None:
        from nornir_netmiko.tasks import netmiko_send_command, netmiko_send_config

        if access_mode == AccessMode.WRITE:
            task.run(
                task=netmiko_send_config,
                config_commands=commands,
                name="configure device",
            )
            return

        for command in commands:
            task.run(
                task=netmiko_send_command,
                command_string=command,
                name=command,
            )
