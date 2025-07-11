> [!IMPORTANT] 
> This project is under development. All source code and features on the main branch are for the purpose of testing or evaluation and not production ready.

# MFD CLI Client

Module for cli_client (command line interface client) utility for the Intel® Infrastructure Processing Unit (Intel® IPU). It implements the [mfd-base-tool](https://github.com/intel/mfd-tool) abstract class.
The command line interface (CLI) is a client application that connects to and communicates with the Intel® IPU Control Plane.

## Usage

```python
import logging

from mfd_connect import RPyCConnection
from mfd_cli_client import CliClient
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prepare CLI Client
cp_host_mng_ip = '10.10.10.10'
rpyc_connection_cp = RPyCConnection(ip=cp_host_mng_ip)
cli_client = CliClient(connection=rpyc_connection_cp, absolute_path_to_binary_dir='/home/root')

# Get switch stats
get_switch_stats_result = cli_client.get_switch_stats(switch_id=1)
logger.info(f'CLI Client switch stats result: {get_switch_stats_result}')

# Find VFs
vf_amount = 1
find_vf_vsi_result = cli_client.find_vf_vsi(vf_amount=vf_amount)
logger.info(f'Find VSI per VF result: {find_vf_vsi_result}')

# List VSI list entries
vsi_list = cli_client.get_mac_and_vsi_list()
logger.info(f"VSI list entries: {vsi_list}")
```
## Exceptions raised by cli_client module
- `CliClientException`

- `CliClientNotAvailable`

## Implemented Methods

`execute_cli_client_command(self, command: str, *, timeout: int = 120, expected_return_codes: Iterable = frozenset({0})) -> str` - Execute any command passed through command parameter with command line interface client tool.

`get_switch_stats(self, switch_id: int = 1) -> SwitchStats` - Get command line interface client switch stats.

`get_vsi_statistics(self, vsi_id: int = 1) -> VSIStats` - Get command line interface client vsi stats.

`prepare_vm_vsi(self, vf_amount: Union[int, str] = 1) -> None` - For vf_amount VFs, create a VM node and map each VF to a VM node (vf0:vm1, vf1:vm2 ...).

`add_psm_vm_node(self, vm_id: Union[int, str] = 1) -> None` - Creates a VM node in the PSM tree with vm_id.

`add_group_vf2vm(self, psm_vf2vm: Dict[int, List[int]]) -> None:` - From a Dict containing VMs each with a list of VFs, create full vf2vm topology in PSM.

`add_vf_to_vm_node(self, vf_id: Union[int, str] = 0, vm_id: Union[int, str] = 1) -> None` - Attaches a VF to a VM node in the PSM tree.

`find_vf_vsi(self, vf_amount: int = 1) -> Dict` - Find VSI per VF.

`get_mac_and_vsi_list(self) -> List[VsiListEntry]` - Get MAC and VSI list.

`get_tc_priorities_switch(self, switch_id: int = 1) -> TrafficClassCounters` - Get Traffic Class priorities from switch stats.

`apply_up_tc_changes(self, config_file_path: Union[Path,str]) -> None` - Apply the up2tc file configuration changes.

`apply_tuprl_changes(self, config_file_path: Union[Path, str]) -> None:` - Apply the tuprl file configuration changes.

`apply_vmrl_changes(self, config_file_path: Union[Path, str]) -> None:` - Apply the vmrl file configuration changes.

`apply_grl_changes(self, config_file_path: Union[Path, str]) -> None:` - Apply the grl file configuration changes.

`apply_fxprl_changes(self, config_file_path: Union[Path, str]) -> None:` - Apply the fxprl file configuration changes.

`apply_mrl_changes(self, config_file_path: Union[Path, str]) -> None:` - Apply the mrl file configuration changes.

`configure_up_up_translation(self, vsi_id: int = 0, different_value: bool = False) -> None` - Configure UP-UP translation from the CLI tool such that each NUP value maps to same VUP value.

`get_vsi_config_list(self) -> List[VsiConfigListEntry]` - Get list containing all data in the VSI table.

`send_link_change_event_all_pf(self, link_status: str, link_speed: str = "200000Mbps") -> None:` - Send link change event to set link status and speed for all pfs
`send_link_change_event_per_pf(self, link_status: str, link_speed: str = "200000Mbps", pf_num: int = 0, vport_id: Optional[int] = None) -> None:` - Send link change event to set link status and speed for a particular pf and vport

`create_mirror_profile(self, profile_id: int, vsi_id: int) -> None:` - Create mirror profile to mirror packets to the specified vsi

`add_psm_vm_rl(self, vm_id: Union[int, str] = 1, limit: int = 10000, burst: int = 2048) -> None` - Create mirror profile to mirror packets to the specified vsi

`read_qos_vm_info(self) -> Dict[int, Dict[int, List[int]]]` - Query VF2VM mapping and return a dict of host keys, with values of dict of vm keys with list of vsi indexes. Or nothing if they dont exist.

## Implemented structures

```python
@dataclass
class FlowStats:
    """Structure for single direction statistics."""
    traffic_class_counters: List[int]
    packet: int
    discards: int
```
```python
@dataclass
class SwitchStats:
    """Structure for both directions statistics."""
    egress: FlowStats
    ingress: FlowStats
    unicast_packet: int
    multicast_packet: int
    broadcast_packet: int
```

```python
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
```

```python
@dataclass
class VSIStats:
    """Structure for both directions VSI statistics."""

    ingress: VSIFlowStats
    egress: VSIFlowStats
```

```python
@dataclass
class TrafficClassCounters:
    """Structure for both directions Traffic Classes Counter."""
    tx: List[int]
    rx: List[int]
```

```python
@dataclass
class VsiListEntry:
    """Structure for an entry in VSI list containing VSI ID and MAC address."""

    vsi_id: int
    mac: MACAddress
```

```python
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
```

```python
class LinkStatus(IntEnum):
    """Link Status enum represents link state."""

    DOWN = 0
    UP = 1
```

## OS supported:
* Linux

## Issue reporting

If you encounter any bugs or have suggestions for improvements, you're welcome to contribute directly or open an issue [here](https://github.com/intel/mfd-cli-client/issues).
