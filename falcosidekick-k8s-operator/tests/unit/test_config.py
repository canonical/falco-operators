# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for config module."""

import pytest
from pydantic import ValidationError

from config import CharmConfig


class TestCharmConfig:
    """Test CharmConfig class."""

    @pytest.mark.parametrize(
        "port",
        [
            1,  # Minimum valid port
            2801,  # Default port
            8080,  # Common port
            65535,  # Maximum valid port
        ],
    )
    def test_valid_port(self, port):
        """Test CharmConfig with valid port numbers.

        Arrange: Prepare valid port number.
        Act: Create CharmConfig with valid port.
        Assert: Port value is correctly set.
        """
        config = CharmConfig(port=port)
        assert config.port == port

    @pytest.mark.parametrize(
        "port",
        [
            -1,  # Negative port
            0,  # Below valid range
            65536,  # Above valid range
            100000,  # Far above valid range
        ],
    )
    def test_invalid_port(self, port):
        """Test CharmConfig with invalid port numbers.

        Arrange: Prepare invalid port number.
        Act: Create CharmConfig with invalid port.
        Assert: ValidationError is raised with appropriate message.
        """
        with pytest.raises(ValidationError) as exc_info:
            CharmConfig(port=port)
        assert f"Port number {port} is out of valid range" in str(exc_info.value)
