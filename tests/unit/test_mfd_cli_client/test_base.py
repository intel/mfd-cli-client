# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
from textwrap import dedent

import pytest
from mfd_connect import SSHConnection
from mfd_connect.base import ConnectionCompletedProcess

from mfd_cli_client import CliClient
from mfd_cli_client.base import (
    SwitchStats,
    FlowStats,
    TrafficClassCounters,
    VsiListEntry,
    VsiConfigListEntry,
    VSIFlowStats,
    VSIStats,
)
from mfd_typing import OSName, MACAddress


class TestCliClient:
    @pytest.fixture
    def cli_client(self, mocker):
        mocker.patch(
            "mfd_cli_client.CliClient.check_if_available", mocker.create_autospec(CliClient.check_if_available)
        )
        mocker.patch(
            "mfd_cli_client.CliClient.get_version", mocker.create_autospec(CliClient.get_version, return_value="0.0.1")
        )
        mocker.patch(
            "mfd_cli_client.CliClient._get_tool_exec_factory",
            mocker.create_autospec(CliClient._get_tool_exec_factory, return_value="cli_client"),
        )
        connection = mocker.create_autospec(SSHConnection)
        connection.get_os_name.return_value = OSName.LINUX
        cli_client = CliClient(connection=connection)
        mocker.stopall()
        return cli_client

    def test_execute_cli_client_command(self, cli_client):
        output = "Any output"
        cli_client._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )
        assert cli_client.execute_cli_client_command(command="foo") == output

    def test_add_group_vf2vm(self, cli_client, mocker):
        cli_client.add_psm_vm_node = mocker.create_autospec(cli_client.add_psm_vm_node)
        cli_client.add_vf_to_vm_node = mocker.create_autospec(cli_client.add_vf_to_vm_node)

        vf2vm = {0: [0, 1], 1: [2, 3, 4]}
        cli_client.add_group_vf2vm(vf2vm)

        assert cli_client.add_psm_vm_node.call_count == 2
        calls = [
            mocker.call(vm_id=0),
            mocker.call(vm_id=1),
        ]
        assert cli_client.add_psm_vm_node.mock_calls == calls

        assert cli_client.add_vf_to_vm_node.call_count == 5
        calls = [
            mocker.call(vm_id=0, vf_id=0),
            mocker.call(vm_id=0, vf_id=1),
            mocker.call(vm_id=1, vf_id=2),
            mocker.call(vm_id=1, vf_id=3),
            mocker.call(vm_id=1, vf_id=4),
        ]
        assert cli_client.add_vf_to_vm_node.mock_calls == calls

    def test_get_switch_stats(self, cli_client):
        output = dedent(
            """No IP address specified, defaulting to localhost
        ingress packet: 14101 bytes: 1872021
        egress packet: 26553 bytes: 39317252
        unicast packet: 0 bytes: 0
        multicast packet: 0 bytes: 0
        broadcast packet: 0 bytes: 0
        ingress discards packet: 0 bytes: 0
        egress discards packet: 0 bytes: 0
        ingress tc 0 packet counter: 14101
        ingress tc 1 packet counter: 0
        ingress tc 2 packet counter: 0
        ingress tc 3 packet counter: 0
        ingress tc 4 packet counter: 0
        ingress tc 5 packet counter: 0
        ingress tc 6 packet counter: 0
        ingress tc 7 packet counter: 0
        egress tc 0 packet counter: 26553
        egress tc 1 packet counter: 0
        egress tc 2 packet counter: 0
        egress tc 3 packet counter: 0
        egress tc 4 packet counter: 0
        egress tc 5 packet counter: 0
        egress tc 6 packet counter: 0
        egress tc 7 packet counter: 0

        server finished responding ======================="""
        )
        expected_result = SwitchStats(
            egress=FlowStats(traffic_class_counters=[26553, 0, 0, 0, 0, 0, 0, 0], packet=26553, discards=0),
            ingress=FlowStats(traffic_class_counters=[14101, 0, 0, 0, 0, 0, 0, 0], packet=14101, discards=0),
            unicast_packet=0,
            multicast_packet=0,
            broadcast_packet=0,
        )

        cli_client._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )
        test_result = cli_client.get_switch_stats()
        assert test_result == expected_result

    def test_get_vsi_stats(self, cli_client):
        output = dedent(
            """No IP address specified, defaulting to localhost
        ingress packet: 2531962219 bytes: 7192275174349
        ingress unicast packet: 2531957282 bytes: 7192274687817
        ingress multicast packet: 4876 bytes: 479592
        ingress broadcast packet: 11 bytes: 704
        ingress discards packet: 50 bytes: 6236
        ingress errors packet: 0 bytes: 0
        ingress unknown packet: 0 bytes: 0
        egress packet: 2032034557 bytes: 5197300431719
        egress unicast packet: 2032034049 bytes: 5197300387175
        egress multicast packet: 361 bytes: 38370
        egress broadcast packet: 147 bytes: 6174
        egress discards packet: 0 bytes: 0
        egress errors packet: 0 bytes: 0

        server finished responding ======================="""
        )
        expected_result = VSIStats(
            ingress=VSIFlowStats(
                packet=2531962219,
                unicast_packet=2531957282,
                multicast_packet=4876,
                broadcast_packet=11,
                discards_packet=50,
                errors_packet=0,
                unknown_packet=0,
            ),
            egress=VSIFlowStats(
                packet=2032034557,
                unicast_packet=2032034049,
                multicast_packet=361,
                broadcast_packet=147,
                discards_packet=0,
                errors_packet=0,
                unknown_packet=None,
            ),
        )
        cli_client._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )
        test_result = cli_client.get_vsi_statistics()
        assert test_result == expected_result

    def test_get_tc_priorities_switch(self, cli_client, mocker):
        cli_client.get_switch_stats = mocker.create_autospec(
            cli_client.get_switch_stats,
            return_value=SwitchStats(
                egress=FlowStats(traffic_class_counters=[26553, 0, 0, 0, 0, 0, 0, 0], packet=26553, discards=0),
                ingress=FlowStats(traffic_class_counters=[14101, 0, 0, 0, 0, 0, 0, 0], packet=14101, discards=0),
                unicast_packet=0,
                multicast_packet=0,
                broadcast_packet=0,
            ),
        )
        assert cli_client.get_tc_priorities_switch() == TrafficClassCounters(
            tx=[26553, 0, 0, 0, 0, 0, 0, 0], rx=[14101, 0, 0, 0, 0, 0, 0, 0]
        )

    def test_find_vf_vsi(self, cli_client):
        output = dedent(
            """\
        No IP address specified, defaulting to localhost
        fn_id: 0   host_id: 0   is_vf: no  vsi_id: 1   vport_id 1  is_created: yes  is_enabled: yes mac addr: 0:0:0:0:3:14
        |->fn_id: 0   host_id: 0   is_vf: yes vsi_id: 9   vport_id 9  is_created: yes  is_enabled: no mac addr: 0:0:0:0:0:0
        |->fn_id: 1   host_id: 0   is_vf: yes vsi_id: a   vport_id a  is_created: yes  is_enabled: no mac addr: 0:0:0:0:0:0
        |->fn_id: 2   host_id: 0   is_vf: yes vsi_id: b   vport_id b  is_created: yes  is_enabled: no mac addr: 0:0:0:0:0:0
        |->fn_id: 3   host_id: 0   is_vf: yes vsi_id: d   vport_id d  is_created: yes  is_enabled: no mac addr: 0:0:0:0:0:0
        |->fn_id: 4   host_id: 0   is_vf: yes vsi_id: f   vport_id f  is_created: yes  is_enabled: no mac addr: 0:0:0:0:0:0
        |->fn_id: 5   host_id: 0   is_vf: yes vsi_id: 11  vport_id 11 is_created: yes  is_enabled: no mac addr: 0:0:0:0:0:0
        |->fn_id: 6   host_id: 0   is_vf: yes vsi_id: 13  vport_id 13 is_created: yes  is_enabled: no mac addr: 0:0:0:0:0:0
        |->fn_id: 7   host_id: 0   is_vf: yes vsi_id: 14  vport_id 14 is_created: yes  is_enabled: no mac addr: 0:0:0:0:0:0
        |->fn_id: 8   host_id: 0   is_vf: yes vsi_id: c   vport_id c  is_created: yes  is_enabled: no mac addr: 0:0:0:0:0:0
        |->fn_id: 9   host_id: 0   is_vf: yes vsi_id: e   vport_id e  is_created: yes  is_enabled: no mac addr: 0:0:0:0:0:0
        |->fn_id: a   host_id: 0   is_vf: yes vsi_id: 10  vport_id 10 is_created: yes  is_enabled: no mac addr: 0:0:0:0:0:0
        |->fn_id: b   host_id: 0   is_vf: yes vsi_id: 12  vport_id 12 is_created: yes  is_enabled: no mac addr: 0:0:0:0:0:0
        fn_id: 1   host_id: 1   is_vf: no  vsi_id: 0   vport_id 2  is_created: no  is_enabled: no mac addr: 0:0:0:0:3:15
        fn_id: 2   host_id: 2   is_vf: no  vsi_id: 0   vport_id 3  is_created: no  is_enabled: no mac addr: 0:0:0:0:3:16
        fn_id: 3   host_id: 3   is_vf: no  vsi_id: 0   vport_id 4  is_created: no  is_enabled: no mac addr: 0:0:0:0:3:17
        fn_id: 4   host_id: 4   is_vf: no  vsi_id: 0   vport_id 5  is_created: no  is_enabled: no mac addr: 0:0:0:0:3:18
        fn_id: 5   host_id: 5   is_vf: no  vsi_id: 0   vport_id 6  is_created: no  is_enabled: no mac addr: 0:0:0:0:3:19
        fn_id: 6   host_id: 0   is_vf: no  vsi_id: 0   vport_id 408is_created: no  is_enabled: no mac addr: 0:0:0:0:0:0
        fn_id: 7   host_id: 4   is_vf: no  vsi_id: 0   vport_id 408is_created: no  is_enabled: no mac addr: 0:0:0:0:0:0
        fn_id: 8   host_id: 0   is_vf: no  vsi_id: 0   vport_id 8  is_created: no  is_enabled: no mac addr: 0:0:0:0:3:1c
        fn_id: 9   host_id: 1   is_vf: no  vsi_id: 0   vport_id 408is_created: no  is_enabled: no mac addr: 0:0:0:0:3:1d
        fn_id: a   host_id: 2   is_vf: no  vsi_id: 0   vport_id 408is_created: no  is_enabled: no mac addr: 0:0:0:0:3:1e
        fn_id: b   host_id: 3   is_vf: no  vsi_id: 0   vport_id 408is_created: no  is_enabled: no mac addr: 0:0:0:0:3:1f
        fn_id: c   host_id: 4   is_vf: no  vsi_id: 0   vport_id 7  is_created: no  is_enabled: no mac addr: 0:0:0:0:3:20
        fn_id: d   host_id: 5   is_vf: no  vsi_id: 0   vport_id 408is_created: no  is_enabled: no mac addr: 0:0:0:0:0:0
        fn_id: f   host_id: 4   is_vf: no  vsi_id: 0   vport_id 408is_created: no  is_enabled: no mac addr: 0:0:0:0:0:0



        server finished responding ======================="""  # noqa: E501
        )
        expected_result = {
            "0": "9",
            "1": "a",
            "2": "b",
            "3": "d",
            "4": "f",
            "5": "11",
            "6": "13",
            "7": "14",
            "8": "c",
            "9": "e",
            "a": "10",
            "b": "12",
        }

        cli_client._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )
        test_result = cli_client.find_vf_vsi(vf_amount=12)
        assert test_result == expected_result

    def test_get_mac_and_vsi_list(self, cli_client):
        output = dedent(
            """\
        No IP address specified, defaulting to localhost
        fn_id: 0   host_id: 0   is_vf: no  vsi_id: 1   vport_id 1  is_created: yes  is_enabled: yes mac addr: 0:0:0:0:3:14
        fn_id: 1   host_id: 1   is_vf: no  vsi_id: 0   vport_id 2  is_created: no  is_enabled: no mac addr: 0:0:0:0:3:15
        fn_id: 2   host_id: 2   is_vf: no  vsi_id: 0   vport_id 3  is_created: no  is_enabled: no mac addr: 0:0:0:0:3:16
        fn_id: 3   host_id: 3   is_vf: no  vsi_id: 0   vport_id 4  is_created: no  is_enabled: no mac addr: 0:0:0:0:3:17
        fn_id: 4   host_id: 4   is_vf: no  vsi_id: 0   vport_id 5  is_created: no  is_enabled: no mac addr: 0:0:0:0:3:18
        fn_id: 5   host_id: 5   is_vf: no  vsi_id: 0   vport_id 6  is_created: no  is_enabled: no mac addr: 0:0:0:0:3:19
        fn_id: 6   host_id: 0   is_vf: no  vsi_id: 0   vport_id 408is_created: no  is_enabled: no mac addr: 0:0:0:0:3:1a
        fn_id: 7   host_id: 4   is_vf: no  vsi_id: 0   vport_id 408is_created: no  is_enabled: no mac addr: 0:0:0:0:3:1b
        fn_id: 8   host_id: 0   is_vf: no  vsi_id: 0   vport_id 8  is_created: no  is_enabled: no mac addr: 0:0:0:0:3:1c
        fn_id: 9   host_id: 1   is_vf: no  vsi_id: 0   vport_id 408is_created: no  is_enabled: no mac addr: 0:0:0:0:3:1d
        fn_id: a   host_id: 2   is_vf: no  vsi_id: 0   vport_id 408is_created: no  is_enabled: no mac addr: 0:0:0:0:3:1e
        fn_id: b   host_id: 3   is_vf: no  vsi_id: 0   vport_id 408is_created: no  is_enabled: no mac addr: 0:0:0:0:3:1f
        fn_id: c   host_id: 4   is_vf: no  vsi_id: 0   vport_id 7  is_created: no  is_enabled: no mac addr: 0:0:0:0:3:20
        fn_id: d   host_id: 5   is_vf: no  vsi_id: 0   vport_id 408is_created: no  is_enabled: no mac addr: 0:0:0:0:3:21
        fn_id: f   host_id: 4   is_vf: no  vsi_id: 0   vport_id 408is_created: no  is_enabled: no mac addr: 0:0:0:0:3:22
        
        server finished responding =======================
        """  # noqa: E501 W293
        )
        expected_result = [
            VsiListEntry(vsi_id=1, mac=MACAddress("00:00:00:00:03:14")),
            VsiListEntry(vsi_id=0, mac=MACAddress("00:00:00:00:03:15")),
            VsiListEntry(vsi_id=0, mac=MACAddress("00:00:00:00:03:16")),
            VsiListEntry(vsi_id=0, mac=MACAddress("00:00:00:00:03:17")),
            VsiListEntry(vsi_id=0, mac=MACAddress("00:00:00:00:03:18")),
            VsiListEntry(vsi_id=0, mac=MACAddress("00:00:00:00:03:19")),
            VsiListEntry(vsi_id=0, mac=MACAddress("00:00:00:00:03:1a")),
            VsiListEntry(vsi_id=0, mac=MACAddress("00:00:00:00:03:1b")),
            VsiListEntry(vsi_id=0, mac=MACAddress("00:00:00:00:03:1c")),
            VsiListEntry(vsi_id=0, mac=MACAddress("00:00:00:00:03:1d")),
            VsiListEntry(vsi_id=0, mac=MACAddress("00:00:00:00:03:1e")),
            VsiListEntry(vsi_id=0, mac=MACAddress("00:00:00:00:03:1f")),
            VsiListEntry(vsi_id=0, mac=MACAddress("00:00:00:00:03:20")),
            VsiListEntry(vsi_id=0, mac=MACAddress("00:00:00:00:03:21")),
            VsiListEntry(vsi_id=0, mac=MACAddress("00:00:00:00:03:22")),
        ]

        cli_client._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )
        test_result = cli_client.get_mac_and_vsi_list()
        assert test_result == expected_result

    def test_get_mac_and_vsi_list_hex_vsi_id(self, cli_client):
        output = dedent(
            """\
        No IP address specified, defaulting to localhost
        fn_id: 0   host_id: 0   is_vf: no  vsi_id: a   vport_id 1  is_created: yes  is_enabled: yes mac addr: 0:0:0:0:3:14
        fn_id: 1   host_id: 1   is_vf: no  vsi_id: b   vport_id 2  is_created: no  is_enabled: no mac addr: 0:0:0:0:3:15
        fn_id: 2   host_id: 2   is_vf: no  vsi_id: c   vport_id 3  is_created: no  is_enabled: no mac addr: 0:0:0:0:3:16
        fn_id: 3   host_id: 3   is_vf: no  vsi_id: d   vport_id 4  is_created: no  is_enabled: no mac addr: 0:0:0:0:3:17
        fn_id: 4   host_id: 4   is_vf: no  vsi_id: e   vport_id 5  is_created: no  is_enabled: no mac addr: 0:0:0:0:3:18
        fn_id: 5   host_id: 5   is_vf: no  vsi_id: f   vport_id 6  is_created: no  is_enabled: no mac addr: 0:0:0:0:3:19

        server finished responding =======================
        """  # noqa: E501 W293
        )
        expected_result = [
            VsiListEntry(vsi_id=10, mac=MACAddress("00:00:00:00:03:14")),
            VsiListEntry(vsi_id=11, mac=MACAddress("00:00:00:00:03:15")),
            VsiListEntry(vsi_id=12, mac=MACAddress("00:00:00:00:03:16")),
            VsiListEntry(vsi_id=13, mac=MACAddress("00:00:00:00:03:17")),
            VsiListEntry(vsi_id=14, mac=MACAddress("00:00:00:00:03:18")),
            VsiListEntry(vsi_id=15, mac=MACAddress("00:00:00:00:03:19")),
        ]

        cli_client._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )
        test_result = cli_client.get_mac_and_vsi_list()
        assert test_result == expected_result

    def test_prepare_vm_vsi(self, cli_client, mocker):
        cli_client.add_psm_vm_node = mocker.create_autospec(cli_client.add_psm_vm_node)
        cli_client.add_vf_to_vm_node = mocker.create_autospec(cli_client.add_vf_to_vm_node)

        cli_client.prepare_vm_vsi(vf_amount=4)
        assert cli_client.add_psm_vm_node.call_count == 4
        assert cli_client.add_vf_to_vm_node.call_count == 4
        calls = [
            mocker.call(vm_id=1),
            mocker.call(vm_id=2),
            mocker.call(vm_id=3),
            mocker.call(vm_id=4),
        ]
        assert cli_client.add_psm_vm_node.mock_calls == calls
        calls = [
            mocker.call(vm_id=1, vf_id=0),
            mocker.call(vm_id=2, vf_id=1),
            mocker.call(vm_id=3, vf_id=2),
            mocker.call(vm_id=4, vf_id=3),
        ]
        assert cli_client.add_vf_to_vm_node.mock_calls == calls

        cli_client.add_psm_vm_node.reset_mock()
        cli_client.add_vf_to_vm_node.reset_mock()

        cli_client.prepare_vm_vsi("0xb")
        assert cli_client.add_psm_vm_node.call_count == 11
        assert cli_client.add_vf_to_vm_node.call_count == 11
        calls = [
            mocker.call(vm_id="0x1"),
            mocker.call(vm_id="0x2"),
            mocker.call(vm_id="0x3"),
            mocker.call(vm_id="0x4"),
            mocker.call(vm_id="0x5"),
            mocker.call(vm_id="0x6"),
            mocker.call(vm_id="0x7"),
            mocker.call(vm_id="0x8"),
            mocker.call(vm_id="0x9"),
            mocker.call(vm_id="0xa"),
            mocker.call(vm_id="0xb"),
        ]
        assert cli_client.add_psm_vm_node.mock_calls == calls
        calls = [
            mocker.call(vm_id="0x1", vf_id="0x0"),
            mocker.call(vm_id="0x2", vf_id="0x1"),
            mocker.call(vm_id="0x3", vf_id="0x2"),
            mocker.call(vm_id="0x4", vf_id="0x3"),
            mocker.call(vm_id="0x5", vf_id="0x4"),
            mocker.call(vm_id="0x6", vf_id="0x5"),
            mocker.call(vm_id="0x7", vf_id="0x6"),
            mocker.call(vm_id="0x8", vf_id="0x7"),
            mocker.call(vm_id="0x9", vf_id="0x8"),
            mocker.call(vm_id="0xa", vf_id="0x9"),
            mocker.call(vm_id="0xb", vf_id="0xa"),
        ]
        assert cli_client.add_vf_to_vm_node.mock_calls == calls

    def test_add_psm_vm_node(self, cli_client, mocker):
        output = dedent(
            """\
        No IP address specified, defaulting to localhost
        Command Succeeded

        server finished responding ======================="""
        )
        cli_client.execute_cli_client_command = mocker.create_autospec(
            cli_client.execute_cli_client_command, return_value=output
        )
        cli_client.add_psm_vm_node(vm_id=1)
        cmd = [
            mocker.call(command="-b psm -m -c -H 0 --vmid 1"),
        ]
        assert cli_client.execute_cli_client_command.mock_calls == cmd

        cli_client.execute_cli_client_command.reset_mock()
        cli_client.add_psm_vm_node(vm_id="0x1")
        cmd = [
            mocker.call(command="-b psm -m -c -H 0 --vmid 0x1"),
        ]
        assert cli_client.execute_cli_client_command.mock_calls == cmd

        cli_client.execute_cli_client_command.reset_mock()
        cli_client.add_psm_vm_node(vm_id="0xa")
        cmd = [
            mocker.call(command="-b psm -m -c -H 0 --vmid 0xa"),
        ]
        assert cli_client.execute_cli_client_command.mock_calls == cmd

        cli_client.execute_cli_client_command.reset_mock()
        cli_client.add_psm_vm_node(vm_id=10)
        cmd = [
            mocker.call(command="-b psm -m -c -H 0 --vmid 10"),
        ]
        assert cli_client.execute_cli_client_command.mock_calls == cmd

    def test_add_vf_to_vm_node(self, cli_client, mocker):
        output = dedent(
            """\
        No IP address specified, defaulting to localhost
        Command Succeeded

        server finished responding ======================="""
        )
        cli_client.execute_cli_client_command = mocker.create_autospec(
            cli_client.execute_cli_client_command, return_value=output
        )
        cli_client.add_vf_to_vm_node(vm_id=10, vf_id=2)
        cmd = [
            mocker.call(command="-b psm -m -c -H 0 --vfid 2 --vmid 10"),
        ]
        assert cli_client.execute_cli_client_command.mock_calls == cmd
        cli_client.execute_cli_client_command.reset_mock()
        cli_client.add_vf_to_vm_node(vm_id=4, vf_id="0xF")
        cmd = [
            mocker.call(command="-b psm -m -c -H 0 --vfid 0xF --vmid 4"),
        ]
        assert cli_client.execute_cli_client_command.mock_calls == cmd
        cli_client.execute_cli_client_command.reset_mock()
        cli_client.add_vf_to_vm_node(vm_id="0xa", vf_id="0x4")
        cmd = [
            mocker.call(command="-b psm -m -c -H 0 --vfid 0x4 --vmid 0xa"),
        ]
        assert cli_client.execute_cli_client_command.mock_calls == cmd

    def test_apply_up_tc_changes(self, cli_client, mocker):
        output = dedent(
            """\
        No IP address specified, defaulting to localhost
        File successfully processed

        server finished responding ======================="""
        )
        cli_client.execute_cli_client_command = mocker.create_autospec(
            cli_client.execute_cli_client_command, return_value=output
        )
        mocker.patch("mfd_cli_client.base.sleep")
        cli_client.apply_up_tc_changes("file")

    def test_apply_tuprl_changes(self, cli_client, mocker):
        output = dedent(
            """\
        No IP address specified, defaulting to localhost
        Command Succeeded

        server finished responding ======================="""
        )
        cli_client.execute_cli_client_command = mocker.create_autospec(
            cli_client.execute_cli_client_command, return_value=output
        )
        mocker.patch("mfd_cli_client.base.sleep")
        cli_client.apply_tuprl_changes("file")

    def test_apply_vmrl_changes(self, cli_client, mocker):
        output = dedent(
            """\
        No IP address specified, defaulting to localhost
        Command Succeeded

        server finished responding ======================="""
        )
        cli_client.execute_cli_client_command = mocker.create_autospec(
            cli_client.execute_cli_client_command, return_value=output
        )
        mocker.patch("mfd_cli_client.base.sleep")
        cli_client.apply_vmrl_changes("file")

    def test_apply_mrl_changes(self, cli_client, mocker):
        output = dedent(
            """\
        No IP address specified, defaulting to localhost
        Command Succeeded

        server finished responding ======================="""
        )
        cli_client.execute_cli_client_command = mocker.create_autospec(
            cli_client.execute_cli_client_command, return_value=output
        )
        mocker.patch("mfd_cli_client.base.sleep")
        cli_client.apply_mrl_changes("file")

    def test_apply_fxprl_changes(self, cli_client, mocker):
        output = dedent(
            """\
        No IP address specified, defaulting to localhost
        Command Succeeded

        server finished responding ======================="""
        )
        cli_client.execute_cli_client_command = mocker.create_autospec(
            cli_client.execute_cli_client_command, return_value=output
        )
        mocker.patch("mfd_cli_client.base.sleep")
        cli_client.apply_fxprl_changes("file")

    def test_apply_grl_changes(self, cli_client, mocker):
        output = dedent(
            """\
        No IP address specified, defaulting to localhost
        Command Succeeded

        server finished responding ======================="""
        )
        cli_client.execute_cli_client_command = mocker.create_autospec(
            cli_client.execute_cli_client_command, return_value=output
        )
        mocker.patch("mfd_cli_client.base.sleep")
        cli_client.apply_grl_changes("file")

    def test_configure_up_up_translation(self, cli_client, mocker):
        output = dedent(
            """\
        No IP address specified, defaulting to localhost
        Command Succeeded

        server finished responding ======================="""
        )
        calls = [
            mocker.call(command="-b qos -m -v 9 --dir 0 --nup 0 --vup 0"),
            mocker.call(command="-b qos -m -v 9 --dir 0 --nup 1 --vup 1"),
            mocker.call(command="-b qos -m -v 9 --dir 0 --nup 2 --vup 2"),
            mocker.call(command="-b qos -m -v 9 --dir 0 --nup 3 --vup 3"),
            mocker.call(command="-b qos -m -v 9 --dir 0 --nup 4 --vup 4"),
            mocker.call(command="-b qos -m -v 9 --dir 0 --nup 5 --vup 5"),
            mocker.call(command="-b qos -m -v 9 --dir 0 --nup 6 --vup 6"),
            mocker.call(command="-b qos -m -v 9 --dir 0 --nup 7 --vup 7"),
            mocker.call(command="-b qos -m -v 9 --dir 1 --nup 0 --vup 0"),
            mocker.call(command="-b qos -m -v 9 --dir 1 --nup 1 --vup 1"),
            mocker.call(command="-b qos -m -v 9 --dir 1 --nup 2 --vup 2"),
            mocker.call(command="-b qos -m -v 9 --dir 1 --nup 3 --vup 3"),
            mocker.call(command="-b qos -m -v 9 --dir 1 --nup 4 --vup 4"),
            mocker.call(command="-b qos -m -v 9 --dir 1 --nup 5 --vup 5"),
            mocker.call(command="-b qos -m -v 9 --dir 1 --nup 6 --vup 6"),
            mocker.call(command="-b qos -m -v 9 --dir 1 --nup 7 --vup 7"),
        ]
        cli_client.execute_cli_client_command = mocker.create_autospec(
            cli_client.execute_cli_client_command, side_effect=[output] * len(calls)
        )
        cli_client.configure_up_up_translation(vsi_id=9)

        assert cli_client.execute_cli_client_command.mock_calls == calls

    def test_get_vsi_config_list(self, cli_client):
        output = dedent(
            """\
        No IP address specified, defaulting to localhost
        fn_id: 0x0   host_id: 0x0   is_vf: no  vsi_id: 0x1   vport_id 0x0   is_created: yes  is_enabled: yes mac addr: 00:01:00:00:03:14
        fn_id: 0x0   host_id: 0x0   is_vf: no  vsi_id: 0xb   vport_id 0x3   is_created: yes  is_enabled: yes mac addr: 00:0b:00:03:03:14
        |->fn_id: 0x0   host_id: 0x0   is_vf: yes vsi_id: 0xc   vport_id 0x0   is_created: yes  is_enabled: yes mac addr: 00:0c:00:00:03:14
        |->fn_id: 0x1   host_id: 0x0   is_vf: yes vsi_id: 0xd   vport_id 0x0   is_created: yes  is_enabled: yes mac addr: 00:0d:00:00:03:14
        fn_id: 0x1   host_id: 0x1   is_vf: no  vsi_id: 0x0   vport_id 0x0   is_created: no  is_enabled: no mac addr: 00:00:00:00:03:15
        fn_id: 0x5   host_id: 0x5   is_vf: no  vsi_id: 0x10  vport_id 0x1   is_created: yes  is_enabled: no mac addr: 00:10:00:01:03:19
        fn_id: 0xc   host_id: 0x4   is_vf: no  vsi_id: 0x0   vport_id 0x0   is_created: no  is_enabled: no mac addr: 00:00:00:00:03:20

        server finished responding =======================
        """  # noqa: E501 W293
        )

        expected_result = [
            VsiConfigListEntry(
                fn_id=0,
                host_id=0,
                is_vf=False,
                vsi_id=1,
                vport_id=0,
                is_created=True,
                is_enabled=True,
                mac=MACAddress("00:01:00:00:03:14"),
            ),
            VsiConfigListEntry(
                fn_id=0,
                host_id=0,
                is_vf=False,
                vsi_id=11,
                vport_id=3,
                is_created=True,
                is_enabled=True,
                mac=MACAddress("00:0b:00:03:03:14"),
            ),
            VsiConfigListEntry(
                fn_id=0,
                host_id=0,
                is_vf=True,
                vsi_id=12,
                vport_id=0,
                is_created=True,
                is_enabled=True,
                mac=MACAddress("00:0c:00:00:03:14"),
            ),
            VsiConfigListEntry(
                fn_id=1,
                host_id=0,
                is_vf=True,
                vsi_id=13,
                vport_id=0,
                is_created=True,
                is_enabled=True,
                mac=MACAddress("00:0d:00:00:03:14"),
            ),
            VsiConfigListEntry(
                fn_id=1,
                host_id=1,
                is_vf=False,
                vsi_id=0,
                vport_id=0,
                is_created=False,
                is_enabled=False,
                mac=MACAddress("00:00:00:00:03:15"),
            ),
            VsiConfigListEntry(
                fn_id=5,
                host_id=5,
                is_vf=False,
                vsi_id=16,
                vport_id=1,
                is_created=True,
                is_enabled=False,
                mac=MACAddress("00:10:00:01:03:19"),
            ),
            VsiConfigListEntry(
                fn_id=12,
                host_id=4,
                is_vf=False,
                vsi_id=0,
                vport_id=0,
                is_created=False,
                is_enabled=False,
                mac=MACAddress("00:00:00:00:03:20"),
            ),
        ]
        cli_client._connection.execute_command.return_value = ConnectionCompletedProcess(
            return_code=0, args="command", stdout=output, stderr="stderr"
        )
        test_result = cli_client.get_vsi_config_list()
        assert test_result == expected_result

    def test_send_link_change_event_all_pf(self, cli_client, mocker):
        output = dedent(
            """\
        No IP address specified, defaulting to localhost
        Command Succeeded

        server finished responding ======================="""
        )
        cli_client.execute_cli_client_command = mocker.create_autospec(
            cli_client.execute_cli_client_command, return_value=output
        )
        cli_client.send_link_change_event_all_pf(link_status="up", link_speed="100Mbps")
        cmd = [
            mocker.call(command="--event link_change --link_status 1 --link_speed 100Mbps --all_pf"),
        ]
        assert cli_client.execute_cli_client_command.mock_calls == cmd
        cli_client.execute_cli_client_command.reset_mock()
        cli_client.send_link_change_event_all_pf(link_status="down", link_speed="25GB")
        cmd = [
            mocker.call(command="--event link_change --link_status 0 --link_speed 25GB --all_pf"),
        ]
        assert cli_client.execute_cli_client_command.mock_calls == cmd

    def test_send_link_change_event_per_pf(self, cli_client, mocker):
        output = dedent(
            """\
        No IP address specified, defaulting to localhost
        Command Succeeded

        server finished responding ======================="""
        )
        cli_client.execute_cli_client_command = mocker.create_autospec(
            cli_client.execute_cli_client_command, return_value=output
        )
        cli_client.send_link_change_event_per_pf(link_status="up", link_speed="1000Mbps", pf_num=4)
        cmd = [
            mocker.call(command="--event link_change --link_status 1 --link_speed 1000Mbps --pf_num 0x4 "),
        ]
        assert cli_client.execute_cli_client_command.mock_calls == cmd
        cli_client.execute_cli_client_command.reset_mock()
        cli_client.send_link_change_event_per_pf(link_status="down", link_speed="50000Mbps", pf_num=8, vport_id=2)
        cmd = [
            mocker.call(
                command="--event link_change --link_status 0 --link_speed 50000Mbps --pf_num 0x8 --vport_id 0x2"
            ),
        ]
        assert cli_client.execute_cli_client_command.mock_calls == cmd

    def test_create_mirror_profile(self, cli_client, mocker):
        output = dedent(
            """\
        No IP address specified, defaulting to localhost
        Command Succeeded

        server finished responding ======================="""
        )
        cli_client.execute_cli_client_command = mocker.create_autospec(
            cli_client.execute_cli_client_command, return_value=output
        )
        cli_client.create_mirror_profile(profile_id=16, vsi_id=1)
        cmd = [
            mocker.call(command="--modify --config --mir_prof 16 --vsi 1 --func_valid"),
        ]
        assert cli_client.execute_cli_client_command.mock_calls == cmd

    def test_add_psm_vm_rl(self, cli_client, mocker):
        output = dedent(
            """\
        No IP address specified, defaulting to localhost
        Command Succeeded

        server finished responding ======================="""
        )
        cli_client.execute_cli_client_command = mocker.create_autospec(
            cli_client.execute_cli_client_command, return_value=output
        )
        cli_client.add_psm_vm_rl(vm_id=2, limit=500000, burst=4096)
        cmd = [
            mocker.call(command="-b psm -m -c -H 0 --vmid 2 -l 500000 -u 4096"),
        ]
        assert cli_client.execute_cli_client_command.mock_calls == cmd

    def test_read_qos_vm_info(self, cli_client, mocker):
        output = dedent(
            """\
        ===== Host, VM, VF mapping for VMRL  ======

        HOST ID 0

                VM ID 1
                        VF ID: 0, 1,
                VM ID 2
                        VF ID: 2, 3,
                VM ID -1
                        VF ID: 4,
        HOST ID 1

        HOST ID 2

        HOST ID 3

        server finished responding ======================="""
        )
        cli_client.execute_cli_client_command = mocker.Mock(return_value=output)
        ret = cli_client.read_qos_vm_info()
        cmd = [
            mocker.call(command="--query --statistics --vm_qos_info"),
        ]
        assert cli_client.execute_cli_client_command.mock_calls == cmd
        assert ret == {0: {1: [0, 1], 2: [2, 3], -1: [4]}, 1: {}, 2: {}, 3: {}}

        output = dedent(
            """\
        ===== Host, VM, VF mapping for VMRL  ======

        HOST ID 0

        HOST ID 1

        HOST ID 2

        HOST ID 3

        server finished responding ======================="""
        )

        cli_client.execute_cli_client_command = mocker.Mock(return_value=output)
        ret = cli_client.read_qos_vm_info()
        assert ret == {0: {}, 1: {}, 2: {}, 3: {}}
