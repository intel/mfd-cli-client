# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for command line interface client."""

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from time import sleep
from typing import Optional, Iterable, Dict, Union, List
from enum import IntEnum

from mfd_common_libs import add_logging_level, log_levels, os_supported
from mfd_base_tool import ToolTemplate
from mfd_typing import OSName, MACAddress

from .exceptions import CliClientException, CliClientNotAvailable

logger = logging.getLogger(__name__)
add_logging_level("MODULE_DEBUG", log_levels.MODULE_DEBUG)


@dataclass
class FlowStats:
    """Structure for single direction statistics."""

    traffic_class_counters: List[int]
    packet: int
    discards: int


@dataclass
class SwitchStats:
    """Structure for both directions statistics."""

    egress: FlowStats
    ingress: FlowStats
    unicast_packet: int
    multicast_packet: int
    broadcast_packet: int


@dataclass
class VSIFlowStats:
    """Structure for VSI statistics."""

    packet: int
    unicast_packet: int
    multicast_packet: int
    broadcast_packet: int
    discards_packet: int
    errors_packet: int
    unknown_packet: int | None = None


@dataclass
class VSIStats:
    """Structure for both directions VSI statistics."""

    ingress: VSIFlowStats
    egress: VSIFlowStats


@dataclass
class TrafficClassCounters:
    """Structure for both directions Traffic Classes Counter."""

    tx: List[int]
    rx: List[int]


@dataclass
class VsiListEntry:
    """Structure for an entry in VSI list containing VSI ID and MAC address."""

    vsi_id: int
    mac: MACAddress


@dataclass
class VsiConfigListEntry:
    """Structure for an entry in VSI Config list containing all fields."""

    fn_id: int
    host_id: int
    is_vf: bool
    vsi_id: int
    vport_id: int
    is_created: bool
    is_enabled: bool
    mac: MACAddress


class LinkStatus(IntEnum):
    """Link Status enum represents link state."""

    DOWN = 0
    UP = 1


class CliClient(ToolTemplate):
    """Module for command line interface client tool."""

    tool_executable_name = "cli_client"
    ALL_USER_PRIORITY_TRAFFIC_CLASS = 8

    __init__ = os_supported(OSName.LINUX)(ToolTemplate.__init__)

    def _get_tool_exec_factory(self) -> str:
        """Get correct tool name."""
        return self.tool_executable_name

    def _apply_config_changes(self, module: str, success_val: str, config_file_path: Union[Path, str]) -> None:
        """
        Apply qos config file change (VMRL, TUPRL ect.) through the cli_client.

        :param config_file_path: Path to config file.
        :param module: Module to modify.
        :param success_val: Expected lower of success string.
        :raises CliClientException: on failure.
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg="Apply the CP configuration changes.")
        output = self.execute_cli_client_command(command=f"-b qos -m -C {module} -f {config_file_path}")
        if success_val in output.lower():
            logger.log(level=log_levels.MODULE_DEBUG, msg=f"Configure and update {module} passed.")
        else:
            raise CliClientException(f"Configure and update {module} failed.")
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Wait 10 sec for update {config_file_path} file.")
        sleep(10)

    def check_if_available(self) -> None:
        """
        Check if tool is available in system.

        :raises CliClientNotAvailable: when tool not available.
        """
        self._connection.execute_command(f"{self._tool_exec} -h", custom_exception=CliClientNotAvailable)

    def execute_cli_client_command(
        self, command: str, *, timeout: int = 120, expected_return_codes: Iterable = frozenset({0})
    ) -> str:
        """
        Execute any command passed through command parameter with command line interface client tool.

        :param command: Command to execute using command line interface client tool.
        :param timeout: Maximum wait time for command to execute.
        :param expected_return_codes: Return codes to be considered acceptable
        :return: Command output for user to verify it.
        """
        command = f"{self._tool_exec} {command}"
        output = self._connection.execute_command(
            command, timeout=timeout, expected_return_codes=expected_return_codes
        ).stdout
        return output

    def get_version(self) -> Optional[str]:
        """
        Get version of tool.

        :return: Version of tool
        """
        logger.log(level=log_levels.MODULE_DEBUG, msg=f"Tool version is not available for {self.tool_executable_name}")
        return "N/A"

    def get_switch_stats(self, switch_id: int = 1) -> SwitchStats:
        """
        Get command line interface client switch stats.

        :param switch_id: switch ID
        :return: Stats for both directions
        """
        command = f"--query --statistics --switch {switch_id}"
        # w/a because the first execution of this command never shows refreshed stats.
        self.execute_cli_client_command(command=command)
        output = self.execute_cli_client_command(command=command)
        rx_stats = FlowStats([0], 0, 0)
        tx_stats = FlowStats([0], 0, 0)
        unicast_counter = multicast_counter = broadcast_counter = 0

        for direction_in_output, direction_in_stats in zip(["egress", "ingress"], ["tx", "rx"]):
            traffic_classes_packet_counter = [0] * self.ALL_USER_PRIORITY_TRAFFIC_CLASS
            packet_counter = discards_counter = 0
            for traffic_class in range(self.ALL_USER_PRIORITY_TRAFFIC_CLASS):
                tc_counter_regex = rf"{direction_in_output}\stc\s{traffic_class}\spacket\scounter:\s(?P<counter>\d+)"
                match = re.search(tc_counter_regex, output)
                if match:
                    traffic_classes_packet_counter[traffic_class] = int(match.group("counter"))

            packet_counter_regex = rf"{direction_in_output}\spacket:\s(?P<counter>\d+)\sbytes"
            match = re.search(packet_counter_regex, output)
            if match:
                packet_counter = int(match.group("counter"))

            discards_counter_regex = rf"{direction_in_output}\sdiscards\spacket:\s(?P<counter>\d+)\sbytes"
            match = re.search(discards_counter_regex, output)
            if match:
                discards_counter = int(match.group("counter"))

            if "tx" == direction_in_stats:
                tx_stats = FlowStats(traffic_classes_packet_counter, packet_counter, discards_counter)
            else:
                rx_stats = FlowStats(traffic_classes_packet_counter, packet_counter, discards_counter)

        unicast_counter_regex = r"unicast\spacket:\s(?P<counter>\d+)\sbytes"
        match = re.search(unicast_counter_regex, output)
        if match:
            unicast_counter = int(match.group("counter"))

        multicast_counter_regex = r"multicast\spacket:\s(?P<counter>\d+)\sbytes"
        match = re.search(multicast_counter_regex, output)
        if match:
            multicast_counter = int(match.group("counter"))

        broadcast_counter_regex = r"broadcast\spacket:\s(?P<counter>\d+)\sbytes"
        match = re.search(broadcast_counter_regex, output)
        if match:
            broadcast_counter = int(match.group("counter"))

        return SwitchStats(tx_stats, rx_stats, unicast_counter, multicast_counter, broadcast_counter)

    def get_vsi_statistics(self, vsi_id: int = 1) -> VSIStats:
        """
        Get command line interface client vsi stats.

        :param vsi_id: VSI ID
        :return: Stats for both directions
        """
        command = f"--query --statistics --vsi {vsi_id}"
        # w/a because the first execution of this command never shows refreshed stats.
        self.execute_cli_client_command(command=command)
        output = self.execute_cli_client_command(command=command)
        rx_stats = VSIFlowStats(0, 0, 0, 0, 0, 0, 0)
        tx_stats = VSIFlowStats(0, 0, 0, 0, 0, 0, 0)
        stats = {}

        for direction in ["ingress", "egress"]:
            patterns = {
                "packet": rf"{direction} packet: (?P<counter>\d+)",
                "unicast_packet": rf"{direction} unicast packet: (?P<counter>\d+)",
                "multicast_packet": rf"{direction} multicast packet: (?P<counter>\d+)",
                "broadcast_packet": rf"{direction} broadcast packet: (?P<counter>\d+)",
                "discards_packet": rf"{direction} discards packet: (?P<counter>\d+)",
                "errors_packet": rf"{direction} errors packet: (?P<counter>\d+)",
                "unknown_packet": rf"{direction} unknown packet: (?P<counter>\d+)",
            }
            for key, regex in patterns.items():
                match = re.search(regex, output)
                stats[key] = int(match.group("counter")) if match else None

            if "ingress" == direction:
                rx_stats = VSIFlowStats(**stats)
            else:
                tx_stats = VSIFlowStats(**stats)

        return VSIStats(rx_stats, tx_stats)

    def add_group_vf2vm(self, psm_vf2vm: Dict[int, List[int]]) -> None:
        """Create a full vf2vm topology in PSM from a dictionary.

        :param psm_vf2vm: Dictionary of VMs to create and list of Vfs to assign to VMs.
        :type psm_vf2vm: Dict[int, List[int]]
        :raises CliClientException: on failure
        """
        for vmid in psm_vf2vm.keys():
            logger.log(level=log_levels.MODULE_DEBUG, msg=f"Creating PSM VM node {vmid}")
            self.add_psm_vm_node(vm_id=vmid)

        for vmid, vfs in psm_vf2vm.items():
            for vf in vfs:
                logger.log(level=log_levels.MODULE_DEBUG, msg=f"Mapping VF: {vf} to VM node: {vmid}")
                self.add_vf_to_vm_node(vm_id=vmid, vf_id=vf)

    def add_psm_vm_node(self, vm_id: Union[int, str] = 1) -> None:
        """
        Add a VM node in the LAN PSM/Work Scheduler tree.

        :param vm_id: VM node id/index. If hex string, then hex string is sent to cli_client.
        :raises CliClientException: on failure
        """
        if isinstance(vm_id, str):
            try:
                int(vm_id, 16)
            except ValueError:
                raise CliClientException("Cannot parse int from hex string")

        output = self.execute_cli_client_command(command=f"-b psm -m -c -H 0 --vmid {vm_id}")
        if "command succeeded" in output.lower():
            logger.log(level=log_levels.MODULE_DEBUG, msg=f"Successfully add PSM VM node id: {vm_id}.")
        else:
            raise CliClientException(f"Error adding PSM VM node id: {vm_id}")

    def add_vf_to_vm_node(self, vf_id: Union[int, str] = 0, vm_id: Union[int, str] = 1) -> None:
        """
        Add a VF to a VM node in the LAN PSM/Work Scheduler tree.

        :param vf_id: VF node id/index. If hex string, hex is sent to cli_client command.
        :raises CliClientException: on failure
        """
        if isinstance(vm_id, str):
            try:
                int(vm_id, 16)
            except ValueError:
                raise CliClientException("Cannot parse int from hex string")
        if isinstance(vf_id, str):
            try:
                int(vf_id, 16)
            except ValueError:
                raise CliClientException("Cannot parse int from hex string")

        output = self.execute_cli_client_command(command=f"-b psm -m -c -H 0 --vfid {vf_id} --vmid {vm_id}")
        if "command succeeded" in output.lower():
            logger.log(level=log_levels.MODULE_DEBUG, msg=f"Successfully add VF {vf_id} to VM node id {vm_id}.")
        else:
            raise CliClientException(f"Error adding VF {vf_id} to VM node id {vm_id}")

    def prepare_vm_vsi(self, vf_amount: Union[int, str] = 1) -> None:
        """
        Pick a VM ID for each VM and associate it to the host.

        :param vf_amount: Number of VFs. If hex string, hex is used in cli_client command.
        """
        use_hex = True
        if isinstance(vf_amount, str):
            try:
                vf_id_list = range(int(vf_amount, 16))
            except ValueError:
                raise CliClientException("Cannot parse int from hex string")
        else:
            vf_id_list = range(vf_amount)
            use_hex = False

        # Start vm nodes at 1
        for node in vf_id_list:
            logger.log(level=log_levels.MODULE_DEBUG, msg=f"Mapping vf_id: {node} to vm node: {node+1}")
            if use_hex:
                self.add_psm_vm_node(vm_id=hex(node + 1))
                self.add_vf_to_vm_node(vf_id=hex(node), vm_id=hex(node + 1))
            else:
                self.add_psm_vm_node(vm_id=node + 1)
                self.add_vf_to_vm_node(vf_id=node, vm_id=node + 1)

    def find_vf_vsi(self, vf_amount: int = 1) -> Dict[str, str]:
        """
        Find VSI per VF.

        :param vf_amount: Number of VFs
        :return: dict with vf vsi
        """
        vf_found = 0
        logger.log(level=log_levels.MODULE_DEBUG, msg="Find VFs VSIs.")
        output = self.get_vsi_config_list()
        vf_vsi = {}

        for vsi in output:
            if vf_found != vf_amount:
                if vsi.is_vf is False:
                    continue
                else:
                    vf_vsi[f"{vsi.fn_id:x}"] = f"{vsi.vsi_id:x}"
                    vf_found = vf_found + 1
            else:
                break

        return vf_vsi

    def get_mac_and_vsi_list(self) -> List[VsiListEntry]:
        """
        Get MAC and VSI list.

        :return: list with entries from VSI list containing VSI ID and MAC address
        """
        output = self.get_vsi_config_list()
        vsi_mac_list = []

        for vsi in output:
            vsi_mac_list.append(VsiListEntry(vsi.vsi_id, vsi.mac))

        return vsi_mac_list

    def get_vsi_config_list(self) -> List[VsiConfigListEntry]:
        """
        Get MAC and VSI list.

        :return: list with entries from VSI list containing all fields in ouput
        """
        output = self.execute_cli_client_command(command="--query --config --verbose")
        pattern = re.compile(
            r"fn_id:\s(?P<fn_id>\w+).*host_id:\s(?P<host_id>\w+).*is_vf:\s(?P<is_vf>(no|yes)).*vsi_id:\s(?P"
            r"<vsi_id>\w+).*vport_id\s(?P<vport_id>\w+).*is_created:\s(?P<is_created>(no|yes)).*is_enabled:"
            r"\s(?P<is_enabled>(no|yes))\smac\saddr:\s(?P<mac>([a-fA-F0-9]{1,2}[:|-]?){6})"
        )
        vsi_config_list = []

        for line in [match.groupdict() for match in pattern.finditer(output)]:
            fn_id = int(line["fn_id"], 16)
            host_id = int(line["host_id"], 16)
            is_vf = True if line["is_vf"] == "yes" else False
            vsi_id = int(line["vsi_id"], 16)
            vport_id = int(line["vport_id"], 16)
            is_created = True if line["is_created"] == "yes" else False
            is_enabled = True if line["is_enabled"] == "yes" else False
            mac = MACAddress(line["mac"])
            vsi_config_list.append(
                VsiConfigListEntry(fn_id, host_id, is_vf, vsi_id, vport_id, is_created, is_enabled, mac)
            )

        return vsi_config_list

    def get_tc_priorities_switch(self, switch_id: int = 1) -> TrafficClassCounters:
        """
        Get Traffic Class priorities from switch stats.

        :param switch_id: switch ID
        :return: Stats of Traffic Classes counter
        """
        switch_stats = self.get_switch_stats(switch_id)
        return TrafficClassCounters(
            rx=switch_stats.ingress.traffic_class_counters, tx=switch_stats.egress.traffic_class_counters
        )

    def apply_up_tc_changes(self, config_file_path: Union[Path, str]) -> None:
        """
        Apply the User Priorities and Traffic Classes configuration changes from file.

        :param config_file_path: Path to user priority/traffic classes file
        :raises CliClientException: on failure
        """
        self._apply_config_changes("TC", "file successfully processed", config_file_path)

    def apply_tuprl_changes(self, config_file_path: Union[Path, str]) -> None:
        """
        Apply the TUPRL configuration changes from file.

        :param config_file_path: Path to user qos_tuprl.cfg file
        :raises CliClientException: on failure
        """
        self._apply_config_changes("TUPRL", "command succeeded", config_file_path)

    def apply_mrl_changes(self, config_file_path: Union[Path, str]) -> None:
        """
        Apply the MRL (Mirror Rate Limit) configuration changes from file.

        :param config_file_path: Path to user qos_mirr_rl.cfg file
        :raises CliClientException: on failure
        """
        self._apply_config_changes("MRL", "command succeeded", config_file_path)

    def apply_fxprl_changes(self, config_file_path: Union[Path, str]) -> None:
        """
        Apply the FXP_RL configuration changes from file.

        :param config_file_path: Path to user qos_mirr_rl.cfg file
        :raises CliClientException: on failure
        """
        self._apply_config_changes("FXP_RL", "command succeeded", config_file_path)

    def apply_vmrl_changes(self, config_file_path: Union[Path, str]) -> None:
        """
        Apply the VMRL (VM Rate Limiter) configuration changes from file.

        :param config_file_path: Path to user qos_vmrl.cfg file
        :raises CliClientException: on failure
        """
        self._apply_config_changes("VMRL", "command succeeded", config_file_path)

    def apply_grl_changes(self, config_file_path: Union[Path, str]) -> None:
        """
        Apply the GRL (Global Rate Limiter) configuration changes from file.

        :param config_file_path: Path to user qos_global_rl.cfg file
        :raises CliClientException: on failure
        """
        self._apply_config_changes("GRL", "command succeeded", config_file_path)

    def configure_up_up_translation(self, vsi_id: int = 0, different_value: bool = False) -> None:
        """
        Configure UP-UP translation from the CLI tool such that each NUP value maps to same VUP value.

        :param vsi_id: vsi id of interface where mapping will be applied
        :param different_value: each NUP value maps to a different VUP value
        :raises CliClientException: on failure
        """
        command_list = []
        for direction in [0, 1]:  # 0 - rx, 1 - tx
            list_of_traffic_classes = range(self.ALL_USER_PRIORITY_TRAFFIC_CLASS)
            if different_value:
                for value, rev_val in zip(list_of_traffic_classes, reversed(list_of_traffic_classes)):
                    cmd = f"-b qos -m -v {vsi_id} --dir {direction} "
                    if direction == 0:
                        cmd += f"--nup {value} --vup {rev_val}"
                    else:
                        cmd += f"--nup {rev_val} --vup {value}"
                    command_list.append(cmd)
            else:
                for value in list_of_traffic_classes:
                    cmd = f"-b qos -m -v {vsi_id} --dir {direction} --nup {value} --vup {value}"
                    command_list.append(cmd)
        for command in command_list:
            output = self.execute_cli_client_command(command=command)
            if "command succeeded" in output.lower():
                logger.log(level=log_levels.MODULE_DEBUG, msg=f"Configure UP-UP translation ({command}) passed.")
            else:
                raise CliClientException(f"Configure UP-UP translation ({command}) failed.")

    def send_link_change_event_all_pf(self, link_status: str, link_speed: str = "200000Mbps") -> None:
        """
        Send a link change event to all pfs.

        :param link_status: Link status ('up' or 'down')
        :param link_speed: Link speed (one of 100MB,1GB,10GB,40GB,20GB,25GB,2_5GB,5GB,xxxMbps(xxx from 1 to 200000))
        :raises CliClientException: on failure
        """
        try:
            cmd = (
                "--event link_change "
                f"--link_status {LinkStatus[link_status.upper()]} --link_speed {link_speed} --all_pf"
            )
        except KeyError as illegal_link:
            raise CliClientException("Link status must be 'up' or 'down'") from illegal_link
        output = self.execute_cli_client_command(command=cmd)
        if "command succeeded" in output.lower():
            logger.log(level=log_levels.MODULE_DEBUG, msg=f"Link change ({cmd}) passed.")
        else:
            raise CliClientException(f"Link change ({cmd}) failed.")

    def send_link_change_event_per_pf(
        self,
        link_status: str,
        link_speed: str = "200000Mbps",
        pf_num: int = 0,
        vport_id: Optional[int] = None,
    ) -> None:
        """
        Send a link change event with link status and link speed to specified pf and vport.

        :param link_status: Link status ('down' or 'up')
        :param link_speed: Link speed (one of 100MB,1GB,10GB,40GB,20GB,25GB,2_5GB,5GB,xxxMbps(xxx from 1 to 200000))
        :param pf_num: pf number on which link changes will be applied.
        :param vport_id: vport id on which link changes will be applied. (optional)
        :raises CliClientException: on failure
        """
        try:
            cmd = f"--event link_change --link_status {LinkStatus[link_status.upper()]} --link_speed {link_speed} "
        except KeyError as illegal_link:
            raise CliClientException("Link status must be 'up' or 'down'") from illegal_link
        cmd += f"--pf_num {hex(pf_num)} "
        cmd += f"--vport_id {hex(vport_id)}" if vport_id else ""
        output = self.execute_cli_client_command(command=cmd)
        if "command succeeded" in output.lower():
            logger.log(level=log_levels.MODULE_DEBUG, msg=f"Link change ({cmd}) passed.")
        else:
            raise CliClientException(f"Link change ({cmd}) failed.")

    def create_mirror_profile(self, profile_id: int, vsi_id: int) -> None:
        """
        Create mirror profile to mirror traffic to a specific vsi.

        :param profile_id: Mirror profile id (must be >= 16)
        :param vsi_id: VSI id where packets will be mirrored
        """
        if profile_id < 16:
            raise CliClientException(f"Mirror profile id {profile_id} must be >=16. Profiles < 16 are reserved.")

        cmd = f"--modify --config --mir_prof {profile_id} --vsi {vsi_id} --func_valid"
        output = self.execute_cli_client_command(command=cmd)
        if "command succeeded" in output.lower():
            logger.log(level=log_levels.MODULE_DEBUG, msg=f"Mirror profile ({cmd}) passed.")
        else:
            raise CliClientException(f"Mirror profile ({cmd}) failed.")

    def add_psm_vm_rl(self, vm_id: Union[int, str] = 1, limit: int = 10000, burst: int = 2048) -> None:
        """
        Add a VM rate limit in the LAN PSM/Work Scheduler tree.

        :param vm_id: VM node id/index. If hex string, then hex string is sent to cli_client.
        :param limit: Rate limit amount.
        :param burst: Burst amount.
        :raises CliClientException: on failure
        """
        if isinstance(vm_id, str):
            try:
                int(vm_id, 16)
            except ValueError:
                raise CliClientException("Cannot parse int from hex string")

        output = self.execute_cli_client_command(command=f"-b psm -m -c -H 0 --vmid {vm_id} -l {limit} -u {burst}")
        if "command succeeded" in output.lower():
            logger.log(level=log_levels.MODULE_DEBUG, msg=f"Successfully added {limit} rate limit on vmid: {vm_id}.")
        else:
            raise CliClientException(f"Error adding PSM VM ratelimit on vmid: {vm_id} rate: {limit} burst: {burst}")

    def read_qos_vm_info(self) -> Dict[int, Dict[int, List[int]]]:
        """
        Query, parse and return the VF2VM mapping currently applied in the cp.

        return: A dictionary of keys hosts, if a host has vms the key is a dict
                of vms which keys are vfs in that vm.

                For example if Host 0 has 2 VMs, each having 2 vfs and there
                is 1 baremetal vf it would return:

                {0: {1: [0, 1], 2: [2, 3], -1: [4]}, 1: {}, 2: {}, 3: {}}
        raises: CliClientException on failure
        """
        output = self.execute_cli_client_command(command="--query --statistics --vm_qos_info")
        if "server finished responding" not in output.lower():
            raise CliClientException("cli_client returned unexpected output when querying vm_qos_info")

        lines = output.split("\n")
        data = {}
        host_id = None
        vm_id = None

        for line in lines:
            if "HOST ID" in line:
                host_id = int(line.split()[-1])
                data[host_id] = {}
            elif "VM ID" in line:
                vm_id = int(line.split()[-1])
                data[host_id][vm_id] = []
            elif "VF ID" in line:
                vf_ids = line.split(":")[-1].strip().split(",")
                vf_ids = [int(vfid) for vfid in vf_ids if vfid]
                data[host_id][vm_id] = vf_ids

        for key in [0, 1, 2, 3]:
            if key not in data:
                raise CliClientException("Error parsing output from vm_qos_info")

        return data
