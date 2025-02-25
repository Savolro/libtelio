# pylint: disable=too-many-lines

import asyncio
import config
import pytest
import re
from config import LIBTELIO_DNS_IPV4, LIBTELIO_DNS_IPV6
from contextlib import AsyncExitStack
from helpers import SetupParameters, setup_api, setup_environment, setup_mesh_nodes
from telio import AdapterType, TelioFeatures
from typing import List, Optional
from utils import testing
from utils.connection import Connection
from utils.connection_tracker import ConnectionLimits
from utils.connection_util import ConnectionTag, generate_connection_tracker_config
from utils.process import ProcessExecError
from utils.router import IPStack


def get_dns_server_address(ip_stack: IPStack) -> str:
    return (
        LIBTELIO_DNS_IPV4
        if ip_stack in [IPStack.IPv4, IPStack.IPv4v6]
        else LIBTELIO_DNS_IPV6
    )


async def query_dns(
    connection: Connection,
    host_name: str,
    expected_output: Optional[List[str]] = None,
    dns_server: Optional[str] = None,
    options: Optional[str] = None,
) -> None:
    response = await testing.wait_normal(
        connection.create_process(
            [
                "nslookup",
                options if options else "-retry=1",
                host_name,
                dns_server if dns_server else LIBTELIO_DNS_IPV4,
            ]
        ).execute()
    )
    if expected_output:
        for expected_str in expected_output:
            assert expected_str in response.get_stdout()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "alpha_ip_stack",
    [
        pytest.param(
            IPStack.IPv4,
            marks=pytest.mark.ipv4,
        ),
        pytest.param(
            IPStack.IPv6,
            marks=pytest.mark.ipv6,
        ),
        pytest.param(
            IPStack.IPv4v6,
            marks=pytest.mark.ipv4v6,
        ),
    ],
)
@pytest.mark.parametrize(
    "beta_ip_stack",
    [
        pytest.param(
            IPStack.IPv4,
            marks=pytest.mark.ipv4,
        ),
        pytest.param(
            IPStack.IPv6,
            marks=pytest.mark.ipv6,
        ),
        pytest.param(
            IPStack.IPv4v6,
            marks=pytest.mark.ipv4v6,
        ),
    ],
)
async def test_dns(
    alpha_ip_stack: IPStack,
    beta_ip_stack: IPStack,
) -> None:
    async with AsyncExitStack() as exit_stack:
        dns_server_address_alpha = get_dns_server_address(alpha_ip_stack)
        dns_server_address_beta = (
            LIBTELIO_DNS_IPV4 if beta_ip_stack == IPStack.IPv4 else LIBTELIO_DNS_IPV6
        )
        env = await setup_mesh_nodes(
            exit_stack,
            [
                SetupParameters(
                    connection_tag=ConnectionTag.DOCKER_CONE_CLIENT_1,
                    connection_tracker_config=generate_connection_tracker_config(
                        ConnectionTag.DOCKER_CONE_CLIENT_1,
                        derp_1_limits=ConnectionLimits(1, 1),
                    ),
                ),
                SetupParameters(
                    connection_tag=ConnectionTag.DOCKER_CONE_CLIENT_2,
                    connection_tracker_config=generate_connection_tracker_config(
                        ConnectionTag.DOCKER_CONE_CLIENT_2,
                        derp_1_limits=ConnectionLimits(1, 1),
                    ),
                ),
            ],
        )
        alpha, beta = env.nodes
        client_alpha, client_beta = env.clients
        connection_alpha, connection_beta = [
            conn.connection for conn in env.connections
        ]

        # These calls should timeout without returning anything, but cache the peer addresses
        with pytest.raises(asyncio.TimeoutError):
            await query_dns(
                connection_alpha, "google.com", dns_server=dns_server_address_alpha
            )

        with pytest.raises(asyncio.TimeoutError):
            await query_dns(
                connection_beta, "google.com", dns_server=dns_server_address_beta
            )

        await client_alpha.enable_magic_dns(["1.1.1.1"])
        await client_beta.enable_magic_dns(["1.1.1.1"])

        # If everything went correctly, these calls should not timeout
        await query_dns(
            connection_alpha, "google.com", dns_server=dns_server_address_alpha
        )
        await query_dns(
            connection_beta, "google.com", dns_server=dns_server_address_beta
        )

        # If the previous calls didn't fail, we can assume that the resolver is running so no need to wait for the timeout and test the validity of the response
        await query_dns(
            connection_alpha, "beta.nord", beta.ip_addresses, dns_server_address_alpha
        )
        await query_dns(
            connection_beta, "alpha.nord", alpha.ip_addresses, dns_server_address_beta
        )

        # Testing if instance can get the IP of self from DNS. See LLT-4246 for more details.
        await query_dns(
            connection_alpha, "alpha.nord", alpha.ip_addresses, dns_server_address_alpha
        )

        # Now we disable magic dns
        await client_alpha.disable_magic_dns()
        await client_beta.disable_magic_dns()

        # And as a result these calls should timeout again
        with pytest.raises(asyncio.TimeoutError):
            await query_dns(
                connection_alpha, "google.com", dns_server=dns_server_address_alpha
            )
        with pytest.raises(asyncio.TimeoutError):
            await query_dns(
                connection_beta, "google.com", dns_server=dns_server_address_beta
            )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "alpha_ip_stack",
    [
        pytest.param(
            IPStack.IPv4,
            marks=pytest.mark.ipv4,
        ),
        pytest.param(
            IPStack.IPv6,
            marks=pytest.mark.ipv6,
        ),
        pytest.param(
            IPStack.IPv4v6,
            marks=pytest.mark.ipv4v6,
        ),
    ],
)
@pytest.mark.xfail(reason="Test is flaky - LLT-4656")
async def test_dns_port(alpha_ip_stack: IPStack) -> None:
    async with AsyncExitStack() as exit_stack:
        dns_server_address_alpha = get_dns_server_address(alpha_ip_stack)
        env = await setup_mesh_nodes(
            exit_stack,
            [
                SetupParameters(
                    connection_tag=ConnectionTag.DOCKER_CONE_CLIENT_1,
                    ip_stack=alpha_ip_stack,
                    connection_tracker_config=generate_connection_tracker_config(
                        ConnectionTag.DOCKER_CONE_CLIENT_1,
                        derp_1_limits=ConnectionLimits(1, 1),
                    ),
                ),
                SetupParameters(
                    connection_tag=ConnectionTag.DOCKER_CONE_CLIENT_2,
                    ip_stack=IPStack.IPv4v6,
                    connection_tracker_config=generate_connection_tracker_config(
                        ConnectionTag.DOCKER_CONE_CLIENT_2,
                        derp_1_limits=ConnectionLimits(1, 1),
                    ),
                ),
            ],
        )
        _, beta = env.nodes
        client_alpha, client_beta = env.clients
        connection_alpha, _ = [conn.connection for conn in env.connections]

        # These call should timeout without returning anything
        with pytest.raises(asyncio.TimeoutError):
            await testing.wait_normal(
                connection_alpha.create_process(
                    ["dig", "@" + dns_server_address_alpha, "-p", "53", "google.com"]
                ).execute()
            )

        await client_alpha.enable_magic_dns(["1.1.1.1"])
        await client_beta.enable_magic_dns(["1.1.1.1"])

        # A DNS request on port 53 should work
        await testing.wait_normal(
            connection_alpha.create_process(
                ["dig", "@" + dns_server_address_alpha, "-p", "53", "google.com"]
            ).execute()
        )

        # A DNS request on a different port should timeout
        with pytest.raises(asyncio.TimeoutError):
            await testing.wait_normal(
                connection_alpha.create_process(
                    ["dig", "@" + dns_server_address_alpha, "-p", "54", "google.com"]
                ).execute()
            )

        # Look for beta on 53 port should work
        alpha_response = await testing.wait_normal(
            connection_alpha.create_process(
                [
                    "dig",
                    "@" + dns_server_address_alpha,
                    "-p",
                    "53",
                    "beta.nord",
                    "A",
                    "beta.nord",
                    "AAAA",
                ]
            ).execute()
        )
        for ip in beta.ip_addresses:
            assert ip in alpha_response.get_stdout()

        # Look for beta on a different port should timeout
        with pytest.raises(asyncio.TimeoutError):
            await testing.wait_normal(
                connection_alpha.create_process(
                    ["dig", "@" + dns_server_address_alpha, "-p", "54", "beta.nord"]
                ).execute()
            )

        # Disable magic dns
        await client_alpha.disable_magic_dns()
        await client_beta.disable_magic_dns()

        # And as a result these calls should timeout again
        with pytest.raises(asyncio.TimeoutError):
            await testing.wait_normal(
                connection_alpha.create_process(
                    ["dig", "@" + dns_server_address_alpha, "-p", "53", "google.com"]
                ).execute()
            )

        with pytest.raises(asyncio.TimeoutError):
            await testing.wait_normal(
                connection_alpha.create_process(
                    ["dig", "@" + dns_server_address_alpha, "-p", "53", "beta.nord"]
                ).execute()
            )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "alpha_ip_stack",
    [
        pytest.param(
            IPStack.IPv4,
            marks=pytest.mark.ipv4,
        ),
        pytest.param(
            IPStack.IPv6,
            marks=pytest.mark.ipv6,
        ),
        pytest.param(
            IPStack.IPv4v6,
            marks=pytest.mark.ipv4v6,
        ),
    ],
)
async def test_vpn_dns(alpha_ip_stack: IPStack) -> None:
    async with AsyncExitStack() as exit_stack:
        dns_server_address = get_dns_server_address(alpha_ip_stack)
        env = await exit_stack.enter_async_context(
            setup_environment(
                exit_stack,
                [
                    SetupParameters(
                        connection_tag=ConnectionTag.DOCKER_CONE_CLIENT_1,
                        ip_stack=alpha_ip_stack,
                        connection_tracker_config=generate_connection_tracker_config(
                            ConnectionTag.DOCKER_CONE_CLIENT_1,
                            vpn_1_limits=ConnectionLimits(1, 1),
                        ),
                        is_meshnet=False,
                    )
                ],
            )
        )
        api = env.api
        alpha, *_ = env.nodes
        client_alpha, *_ = env.clients
        connection, *_ = [conn.connection for conn in env.connections]

        wg_server = config.WG_SERVER

        await client_alpha.connect_to_vpn(
            str(wg_server["ipv4"]), int(wg_server["port"]), str(wg_server["public_key"])
        )

        # After we connect to the VPN, enable magic DNS
        await client_alpha.enable_magic_dns(["1.1.1.1"])

        # Test to see if the module is working correctly
        await query_dns(connection, "google.com", dns_server=dns_server_address)

        # Test if the DNS module preserves CNAME records
        await query_dns(
            connection,
            "www.microsoft.com",
            ["canonical name"],
            dns_server_address,
            "-q=CNAME",
        )

        # Turn off the module and see if it worked
        await client_alpha.disable_magic_dns()

        with pytest.raises(asyncio.TimeoutError):
            await query_dns(connection, "google.com", dns_server=dns_server_address)

        # Test interop with meshnet
        await client_alpha.enable_magic_dns(["1.1.1.1"])
        await client_alpha.set_meshmap(api.get_meshmap(alpha.id, derp_servers=[]))

        await query_dns(connection, "google.com", dns_server=dns_server_address)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "alpha_ip_stack",
    [
        pytest.param(
            IPStack.IPv4,
            marks=pytest.mark.ipv4,
        ),
        pytest.param(
            IPStack.IPv6,
            marks=pytest.mark.ipv6,
        ),
        pytest.param(
            IPStack.IPv4v6,
            marks=pytest.mark.ipv4v6,
        ),
    ],
)
async def test_dns_after_mesh_off(alpha_ip_stack: IPStack) -> None:
    async with AsyncExitStack() as exit_stack:
        dns_server_address = get_dns_server_address(alpha_ip_stack)
        api, (_, beta) = setup_api([(False, alpha_ip_stack), (False, IPStack.IPv4v6)])
        env = await exit_stack.enter_async_context(
            setup_environment(
                exit_stack,
                [
                    SetupParameters(
                        connection_tag=ConnectionTag.DOCKER_CONE_CLIENT_1,
                        connection_tracker_config=generate_connection_tracker_config(
                            ConnectionTag.DOCKER_CONE_CLIENT_1
                        ),
                        derp_servers=[],
                        features=TelioFeatures(ipv6=True),
                    )
                ],
                provided_api=api,
            )
        )
        connection_alpha, *_ = [conn.connection for conn in env.connections]
        client_alpha, *_ = env.clients

        # These calls should timeout without returning anything, but cache the peer addresses
        with pytest.raises(asyncio.TimeoutError):
            await query_dns(
                connection_alpha, "google.com", dns_server=dns_server_address
            )

        await client_alpha.enable_magic_dns(["1.1.1.1"])

        # If everything went correctly, these calls should not timeout
        await query_dns(connection_alpha, "google.com", dns_server=dns_server_address)

        # If the previous calls didn't fail, we can assume that the resolver is running so no need to wait for the timeout and test the validity of the response
        await query_dns(
            connection_alpha, "beta.nord", beta.ip_addresses, dns_server_address
        )

        # Now we disable magic dns
        await client_alpha.set_mesh_off()

        # If everything went correctly, these calls should not timeout
        await query_dns(connection_alpha, "google.com", dns_server=dns_server_address)

        # After mesh off, .nord names should not be resolved anymore, therefore nslookup should fail
        try:
            await query_dns(
                connection_alpha, "beta.nord", dns_server=dns_server_address
            )
        except ProcessExecError as e:
            assert "server can't find beta.nord" in e.stdout


@pytest.mark.asyncio
@pytest.mark.long
@pytest.mark.timeout(60 * 5 + 60)
@pytest.mark.parametrize(
    "alpha_ip_stack",
    [
        pytest.param(
            IPStack.IPv4,
            marks=pytest.mark.ipv4,
        ),
        pytest.param(
            IPStack.IPv6,
            marks=pytest.mark.ipv6,
        ),
        pytest.param(
            IPStack.IPv4v6,
            marks=pytest.mark.ipv4v6,
        ),
    ],
)
async def test_dns_stability(alpha_ip_stack: IPStack) -> None:
    async with AsyncExitStack() as exit_stack:
        dns_server_address = get_dns_server_address(alpha_ip_stack)
        env = await setup_mesh_nodes(
            exit_stack,
            [
                SetupParameters(
                    connection_tag=ConnectionTag.DOCKER_CONE_CLIENT_1,
                    ip_stack=alpha_ip_stack,
                    adapter_type=AdapterType.BoringTun,
                    connection_tracker_config=generate_connection_tracker_config(
                        ConnectionTag.DOCKER_CONE_CLIENT_1,
                        derp_1_limits=ConnectionLimits(1, 1),
                    ),
                ),
                SetupParameters(
                    connection_tag=ConnectionTag.DOCKER_CONE_CLIENT_2,
                    ip_stack=IPStack.IPv4v6,
                    connection_tracker_config=generate_connection_tracker_config(
                        ConnectionTag.DOCKER_CONE_CLIENT_2,
                        derp_1_limits=ConnectionLimits(1, 1),
                    ),
                ),
            ],
        )
        alpha, beta = env.nodes
        client_alpha, client_beta = env.clients
        connection_alpha, connection_beta = [
            conn.connection for conn in env.connections
        ]

        await client_alpha.enable_magic_dns(["1.1.1.1"])
        await client_beta.enable_magic_dns(["1.1.1.1"])

        await query_dns(connection_alpha, "google.com", dns_server=dns_server_address)
        await query_dns(connection_beta, "google.com", dns_server=dns_server_address)

        await query_dns(
            connection_alpha, "beta.nord", beta.ip_addresses, dns_server_address
        )
        await query_dns(
            connection_beta, "alpha.nord", alpha.ip_addresses, dns_server_address
        )

        await asyncio.sleep(60 * 5)

        await query_dns(connection_alpha, "google.com", dns_server=dns_server_address)
        await query_dns(connection_beta, "google.com", dns_server=dns_server_address)

        await query_dns(
            connection_alpha, "beta.nord", beta.ip_addresses, dns_server_address
        )
        await query_dns(
            connection_beta, "alpha.nord", alpha.ip_addresses, dns_server_address
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "alpha_ip_stack",
    [
        pytest.param(
            IPStack.IPv4,
            marks=pytest.mark.ipv4,
        ),
        pytest.param(
            IPStack.IPv6,
            marks=pytest.mark.ipv6,
        ),
        pytest.param(
            IPStack.IPv4v6,
            marks=pytest.mark.ipv4v6,
        ),
    ],
)
async def test_set_meshmap_dns_update(
    alpha_ip_stack: IPStack,
) -> None:
    async with AsyncExitStack() as exit_stack:
        dns_server_address = get_dns_server_address(alpha_ip_stack)
        env = await exit_stack.enter_async_context(
            setup_environment(
                exit_stack,
                [
                    SetupParameters(
                        connection_tag=ConnectionTag.DOCKER_CONE_CLIENT_1,
                        ip_stack=alpha_ip_stack,
                        connection_tracker_config=generate_connection_tracker_config(
                            ConnectionTag.DOCKER_CONE_CLIENT_1
                        ),
                        derp_servers=[],
                    )
                ],
            )
        )
        api = env.api
        alpha, *_ = env.nodes
        connection_alpha, *_ = [conn.connection for conn in env.connections]
        client_alpha, *_ = env.clients

        await client_alpha.enable_magic_dns([])

        # We should not be able to resolve beta yet, since it's not registered
        try:
            await query_dns(
                connection_alpha, "beta.nord", dns_server=dns_server_address
            )
        except ProcessExecError as e:
            assert "server can't find beta.nord" in e.stdout

        beta = api.default_config_one_node(ip_stack=IPStack.IPv4v6)

        # Check if setting meshnet updates nord names for dns resolver
        await client_alpha.set_meshmap(api.get_meshmap(alpha.id, derp_servers=[]))

        await query_dns(
            connection_alpha, "beta.nord", [beta.ip_addresses[0]], dns_server_address
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "alpha_ip_stack",
    [
        pytest.param(
            IPStack.IPv4,
            marks=pytest.mark.ipv4,
        ),
        pytest.param(
            IPStack.IPv6,
            marks=pytest.mark.ipv6,
        ),
        pytest.param(
            IPStack.IPv4v6,
            marks=pytest.mark.ipv4v6,
        ),
    ],
)
async def test_dns_update(alpha_ip_stack: IPStack) -> None:
    async with AsyncExitStack() as exit_stack:
        dns_server_address = get_dns_server_address(alpha_ip_stack)
        env = await exit_stack.enter_async_context(
            setup_environment(
                exit_stack,
                [
                    SetupParameters(
                        connection_tag=ConnectionTag.DOCKER_CONE_CLIENT_1,
                        ip_stack=alpha_ip_stack,
                        connection_tracker_config=generate_connection_tracker_config(
                            ConnectionTag.DOCKER_CONE_CLIENT_1,
                            vpn_1_limits=ConnectionLimits(1, 1),
                        ),
                        is_meshnet=False,
                    )
                ],
            )
        )
        connection, *_ = [conn.connection for conn in env.connections]
        client_alpha, *_ = env.clients

        wg_server = config.WG_SERVER

        await client_alpha.connect_to_vpn(
            str(wg_server["ipv4"]), int(wg_server["port"]), str(wg_server["public_key"])
        )

        # Don't forward anything yet
        await client_alpha.enable_magic_dns([])

        with pytest.raises(asyncio.TimeoutError):
            await query_dns(connection, "google.com", dns_server=dns_server_address)

        # Update forward dns and check if it works now
        await client_alpha.enable_magic_dns(["1.1.1.1"])

        await query_dns(
            connection, "google.com", ["Name:	google.com\nAddress:"], dns_server_address
        )


@pytest.mark.asyncio
async def test_dns_duplicate_requests_on_multiple_forward_servers() -> None:
    async with AsyncExitStack() as exit_stack:
        FIRST_DNS_SERVER = "8.8.8.8"
        SECOND_DNS_SERVER = "1.1.1.1"
        env = await setup_mesh_nodes(
            exit_stack,
            [
                SetupParameters(
                    connection_tag=ConnectionTag.DOCKER_CONE_CLIENT_1,
                    ip_stack=IPStack.IPv4v6,
                    connection_tracker_config=generate_connection_tracker_config(
                        ConnectionTag.DOCKER_CONE_CLIENT_1
                    ),
                    derp_servers=[],
                )
            ],
        )
        connection_alpha, *_ = [conn.connection for conn in env.connections]
        client_alpha, *_ = env.clients

        process = await exit_stack.enter_async_context(
            connection_alpha.create_process(
                [
                    "tcpdump",
                    "--immediate-mode",
                    "-ni",
                    "eth0",
                    "udp",
                    "and",
                    "port",
                    "53",
                    "-l",
                ]
            ).run()
        )
        await asyncio.sleep(1)

        await client_alpha.enable_magic_dns([FIRST_DNS_SERVER, SECOND_DNS_SERVER])
        await asyncio.sleep(1)

        await query_dns(connection_alpha, "google.com")
        await asyncio.sleep(1)

        tcpdump_stdout = process.get_stdout()
        results = set(re.findall(
            r".* IP .* > (?P<dest_ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\.\d{1,5}: .* A\?.*",
            tcpdump_stdout,
        ))  # fmt: skip

        assert results in ({FIRST_DNS_SERVER}, {SECOND_DNS_SERVER}), tcpdump_stdout


@pytest.mark.asyncio
async def test_dns_aaaa_records() -> None:
    async with AsyncExitStack() as exit_stack:
        api, (_, beta) = setup_api([(False, IPStack.IPv4v6), (False, IPStack.IPv4v6)])
        env = await exit_stack.enter_async_context(
            setup_environment(exit_stack, [SetupParameters()], provided_api=api)
        )
        connection_alpha, *_ = [conn.connection for conn in env.connections]
        client_alpha, *_ = env.clients

        await client_alpha.enable_magic_dns(["1.1.1.1"])

        await query_dns(connection_alpha, "beta.nord", beta.ip_addresses)


@pytest.mark.asyncio
async def test_dns_nickname() -> None:
    async with AsyncExitStack() as exit_stack:
        api, (alpha, beta) = setup_api(
            [(False, IPStack.IPv4v6), (False, IPStack.IPv4v6)]
        )
        api.assign_nickname(alpha.id, "johnny")
        api.assign_nickname(beta.id, "yoko")

        env = await setup_mesh_nodes(
            exit_stack,
            [
                SetupParameters(
                    connection_tag=ConnectionTag.DOCKER_CONE_CLIENT_1,
                    connection_tracker_config=generate_connection_tracker_config(
                        ConnectionTag.DOCKER_CONE_CLIENT_1,
                        derp_1_limits=ConnectionLimits(1, 1),
                    ),
                    features=TelioFeatures(nicknames=True),
                ),
                SetupParameters(
                    connection_tag=ConnectionTag.DOCKER_CONE_CLIENT_2,
                    connection_tracker_config=generate_connection_tracker_config(
                        ConnectionTag.DOCKER_CONE_CLIENT_2,
                        derp_1_limits=ConnectionLimits(1, 1),
                    ),
                    features=TelioFeatures(nicknames=True),
                ),
            ],
            provided_api=api,
        )
        client_alpha, client_beta = env.clients
        connection_alpha, connection_beta = [
            conn.connection for conn in env.connections
        ]

        await client_alpha.enable_magic_dns([])
        await client_beta.enable_magic_dns([])

        await query_dns(connection_alpha, "yoko.nord", beta.ip_addresses)
        await query_dns(connection_alpha, "johnny.nord", alpha.ip_addresses)

        await query_dns(connection_beta, "johnny.nord", alpha.ip_addresses)
        await query_dns(connection_beta, "yoko.nord", beta.ip_addresses)


@pytest.mark.asyncio
async def test_dns_change_nickname() -> None:
    async with AsyncExitStack() as exit_stack:
        api, (alpha, beta) = setup_api(
            [(False, IPStack.IPv4v6), (False, IPStack.IPv4v6)]
        )
        api.assign_nickname(alpha.id, "johnny")
        api.assign_nickname(beta.id, "yoko")
        env = await setup_mesh_nodes(
            exit_stack,
            [
                SetupParameters(
                    connection_tag=ConnectionTag.DOCKER_CONE_CLIENT_1,
                    connection_tracker_config=generate_connection_tracker_config(
                        ConnectionTag.DOCKER_CONE_CLIENT_1,
                        derp_1_limits=ConnectionLimits(1, 1),
                    ),
                    features=TelioFeatures(nicknames=True),
                ),
                SetupParameters(
                    connection_tag=ConnectionTag.DOCKER_CONE_CLIENT_2,
                    connection_tracker_config=generate_connection_tracker_config(
                        ConnectionTag.DOCKER_CONE_CLIENT_2,
                        derp_1_limits=ConnectionLimits(1, 1),
                    ),
                    features=TelioFeatures(nicknames=True),
                ),
            ],
            provided_api=api,
        )
        client_alpha, client_beta = env.clients
        connection_alpha, connection_beta = [
            conn.connection for conn in env.connections
        ]

        await client_alpha.enable_magic_dns([])
        await client_beta.enable_magic_dns([])

        # Set new meshmap with different nicknames
        api.assign_nickname(alpha.id, "rotten")
        api.assign_nickname(beta.id, "ono")
        await client_alpha.set_meshmap(api.get_meshmap(alpha.id, derp_servers=[]))
        await client_beta.set_meshmap(api.get_meshmap(beta.id, derp_servers=[]))

        with pytest.raises(ProcessExecError):
            await query_dns(connection_alpha, "yoko.nord")
        with pytest.raises(ProcessExecError):
            await query_dns(connection_alpha, "johnny.nord")
        with pytest.raises(ProcessExecError):
            await query_dns(connection_beta, "yoko.nord")
        with pytest.raises(ProcessExecError):
            await query_dns(connection_beta, "johnny.nord")

        await query_dns(connection_alpha, "ono.nord", beta.ip_addresses)
        await query_dns(connection_alpha, "rotten.nord", alpha.ip_addresses)

        await query_dns(connection_beta, "rotten.nord", alpha.ip_addresses)
        await query_dns(connection_beta, "ono.nord", beta.ip_addresses)

        # Set new meshmap removing nicknames
        api.reset_nickname(alpha.id)
        api.reset_nickname(beta.id)
        await client_alpha.set_meshmap(api.get_meshmap(alpha.id, derp_servers=[]))
        await client_beta.set_meshmap(api.get_meshmap(beta.id, derp_servers=[]))

        with pytest.raises(ProcessExecError):
            await query_dns(connection_alpha, "ono.nord")

        with pytest.raises(ProcessExecError):
            await query_dns(connection_alpha, "rotten.nord")

        with pytest.raises(ProcessExecError):
            await query_dns(connection_beta, "rotten.nord")

        with pytest.raises(ProcessExecError):
            await query_dns(connection_beta, "ono.nord")


@pytest.mark.asyncio
async def test_dns_wildcarded_records() -> None:
    async with AsyncExitStack() as exit_stack:
        api, (alpha, beta) = setup_api(
            [(False, IPStack.IPv4v6), (False, IPStack.IPv4v6)]
        )
        api.assign_nickname(alpha.id, "johnny")
        api.assign_nickname(beta.id, "yoko")
        env = await setup_mesh_nodes(
            exit_stack,
            [
                SetupParameters(
                    connection_tag=ConnectionTag.DOCKER_CONE_CLIENT_1,
                    connection_tracker_config=generate_connection_tracker_config(
                        ConnectionTag.DOCKER_CONE_CLIENT_1,
                        derp_1_limits=ConnectionLimits(1, 1),
                    ),
                    features=TelioFeatures(nicknames=True),
                ),
                SetupParameters(
                    connection_tag=ConnectionTag.DOCKER_CONE_CLIENT_2,
                    connection_tracker_config=generate_connection_tracker_config(
                        ConnectionTag.DOCKER_CONE_CLIENT_2,
                        derp_1_limits=ConnectionLimits(1, 1),
                    ),
                    features=TelioFeatures(nicknames=True),
                ),
            ],
            provided_api=api,
        )
        client_alpha, client_beta = env.clients
        connection_alpha, connection_beta = [
            conn.connection for conn in env.connections
        ]

        await client_alpha.enable_magic_dns([])
        await client_beta.enable_magic_dns([])

        await query_dns(connection_alpha, "myserviceA.alpha.nord", alpha.ip_addresses)
        await query_dns(connection_alpha, "myserviceB.johnny.nord", alpha.ip_addresses)
        await query_dns(connection_alpha, "herservice.yoko.nord", beta.ip_addresses)

        await query_dns(connection_beta, "myserviceC.beta.nord", beta.ip_addresses)
        await query_dns(connection_beta, "myserviceD.yoko.nord", beta.ip_addresses)
        await query_dns(connection_beta, "hisservice.johnny.nord", alpha.ip_addresses)
