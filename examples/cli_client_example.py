# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
import logging

from mfd_connect import RPyCConnection
from mfd_cli_client import CliClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prepare CLI Client
cp_host_mng_ip = "10.10.10.10"
rpyc_connection_cp = RPyCConnection(ip=cp_host_mng_ip)
cli_client = CliClient(connection=rpyc_connection_cp, absolute_path_to_binary_dir="/home/root")

# Get switch stats
get_switch_stats_result = cli_client.get_switch_stats(switch_id=1)
logger.info(f"CLI Client switch stats result: {get_switch_stats_result}")

# Get VSI stats
get_vsi_stats_result = cli_client.get_vsi_statistics(vsi_id=1)
logger.info(f"CLI CLient vsi stats result: {get_vsi_stats_result}")

# Find VFs
vf_amount = 1
find_vf_vsi_result = cli_client.find_vf_vsi(vf_amount=vf_amount)
logger.info(f"Find VSI per VF result: {find_vf_vsi_result}")

# List VSI list entries
vsi_list = cli_client.get_mac_and_vsi_list()
logger.info(f"VSI list entries: {vsi_list}")
