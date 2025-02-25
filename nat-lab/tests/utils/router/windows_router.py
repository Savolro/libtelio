import random
from .router import Router, IPProto, IPStack
from config import LIBTELIO_IPV6_WG_SUBNET
from contextlib import asynccontextmanager
from typing import AsyncIterator, List
from utils.connection import Connection
from utils.process import ProcessExecError


class WindowsRouter(Router):
    _connection: Connection
    _interface_name: str

    def __init__(self, connection: Connection, ip_stack: IPStack):
        super().__init__(ip_stack)
        self._connection = connection
        self._interface_name = "wintun10_" + str(random.randint(0, 256))

    def get_interface_name(self) -> str:
        return self._interface_name

    async def setup_interface(self, addresses: List[str]) -> None:
        for address in addresses:
            addr_proto = self.check_ip_address(address)

            if addr_proto == IPProto.IPv4:
                await self._connection.create_process(
                    [
                        "netsh",
                        "interface",
                        "ipv4",
                        "add",
                        "address",
                        self._interface_name,
                        address,
                        "255.255.255.255",
                    ]
                ).execute()
            elif addr_proto == IPProto.IPv6:
                await self._connection.create_process(
                    [
                        "netsh",
                        "interface",
                        "ipv6",
                        "add",
                        "address",
                        self._interface_name,
                        address + "/128",
                    ]
                ).execute()

    async def create_meshnet_route(self) -> None:
        if self.ip_stack in [IPStack.IPv4, IPStack.IPv4v6]:
            try:
                await self._connection.create_process(
                    [
                        "netsh",
                        "interface",
                        "ipv4",
                        "add",
                        "route",
                        "100.64.0.0/10",
                        self._interface_name,
                    ]
                ).execute()
            except ProcessExecError as exception:
                if exception.stdout.find("The object already exists.") < 0:
                    raise exception

        if self.ip_stack in [IPStack.IPv6, IPStack.IPv4v6]:
            try:
                await self._connection.create_process(
                    [
                        "netsh",
                        "interface",
                        "ipv6",
                        "add",
                        "route",
                        LIBTELIO_IPV6_WG_SUBNET + "::/64",
                        self._interface_name,
                    ]
                ).execute()
            except ProcessExecError as exception:
                if exception.stdout.find("The object already exists.") < 0:
                    raise exception

    async def create_vpn_route(self) -> None:
        try:
            await self._connection.create_process(
                [
                    "netsh",
                    "interface",
                    "ipv4",
                    "add",
                    "route",
                    "0.0.0.0/0",
                    self._interface_name,
                    "metric=1",
                ]
            ).execute()
        except ProcessExecError as exception:
            if exception.stdout.find("The object already exists.") < 0:
                raise exception

        try:
            await self._connection.create_process(
                [
                    "netsh",
                    "interface",
                    "ipv6",
                    "add",
                    "route",
                    "::/0",
                    self._interface_name,
                ]
            ).execute()
        except ProcessExecError as exception:
            if exception.stdout.find("The object already exists.") < 0:
                raise exception

    async def delete_interface(self) -> None:
        pass

    async def delete_vpn_route(self) -> None:
        assert self._interface_name

        if self.ip_stack in [IPStack.IPv4, IPStack.IPv4v6]:
            try:
                await self._connection.create_process(
                    [
                        "netsh",
                        "interface",
                        "ipv4",
                        "delete",
                        "route",
                        "0.0.0.0/0",
                        self._interface_name,
                    ]
                ).execute()
            except ProcessExecError as exception:
                if (
                    exception.stdout.find(
                        "The filename, directory name, or volume label syntax is"
                        " incorrect."
                    )
                    < 0
                    and exception.stdout.find("Element not found.") < 0
                ):
                    raise exception

        if self.ip_stack in [IPStack.IPv6, IPStack.IPv4v6]:
            try:
                await self._connection.create_process(
                    [
                        "netsh",
                        "interface",
                        "ipv6",
                        "delete",
                        "route",
                        "::/0",
                        self._interface_name,
                    ]
                ).execute()
            except ProcessExecError as exception:
                if (
                    exception.stdout.find(
                        "The filename, directory name, or volume label syntax is"
                        " incorrect."
                    )
                    < 0
                    and exception.stdout.find("Element not found.") < 0
                ):
                    raise exception

    async def create_exit_node_route(self) -> None:
        pass

    async def delete_exit_node_route(self) -> None:
        pass

    @asynccontextmanager
    async def disable_path(
        self, address: str  # pylint: disable=unused-argument
    ) -> AsyncIterator:
        yield

    @asynccontextmanager
    async def break_tcp_conn_to_host(
        self, address: str  # pylint: disable=unused-argument
    ) -> AsyncIterator:
        yield

    @asynccontextmanager
    async def break_udp_conn_to_host(
        self, address: str  # pylint: disable=unused-argument
    ) -> AsyncIterator:
        yield

    @asynccontextmanager
    async def reset_upnpd(self) -> AsyncIterator:
        yield
