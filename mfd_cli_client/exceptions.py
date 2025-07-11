# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Exceptions for command line interface client module."""

from mfd_base_tool.exceptions import ToolNotAvailable


class CliClientException(Exception):
    """Exception for command line interface client module."""


class CliClientNotAvailable(ToolNotAvailable, CliClientException):
    """Handle tool not available exception."""
