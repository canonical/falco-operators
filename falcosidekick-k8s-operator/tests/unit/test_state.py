# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for Falco state module."""

from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from config import CharmConfig, InvalidCharmConfigError
from state import CharmState


class TestCharmState:
    """Test CharmState class."""

    def test_charm_state_creation(self):
        """Test creating a CharmState instance.

        Arrange: Prepare port value and loki fields.
        Act: Create CharmState instance.
        Assert: CharmState has correct port value.
        """
        state = CharmState(
            falcosidekick_listenport=8080,
            falcosidekick_loki_endpoint="/loki/api/v1/push",
            falcosidekick_loki_hostport="http://loki:3100",
        )
        assert state.falcosidekick_listenport == 8080

    @pytest.mark.parametrize(
        "port",
        [
            2801,  # Default port
            8080,  # Custom port
            1,  # Minimum valid port
            65535,  # Maximum valid port
        ],
    )
    def test_from_charm_with_valid_config(self, port):
        """Test CharmState.from_charm with valid configuration.

        Arrange: Set up mock charm with valid port configuration.
        Act: Create CharmState from charm.
        Assert: CharmState has correct port value from config.
        """
        # Arrange
        mock_charm = MagicMock()
        mock_charm.load_config.return_value = CharmConfig(port=port)

        mock_loki_relation = MagicMock()
        mock_loki_relation.loki_endpoints = []

        # Act
        state = CharmState.from_charm(mock_charm, mock_loki_relation)

        # Assert
        assert state.falcosidekick_listenport == port
        mock_charm.load_config.assert_called_once_with(CharmConfig)

    @pytest.mark.parametrize(
        "port",
        [
            0,  # Below valid range
            -1,  # Negative
            65536,  # Above valid range
        ],
    )
    def test_from_charm_with_invalid_config(self, port):
        """Test CharmState.from_charm with invalid configuration.

        Arrange: Set up mock charm with invalid port configuration.
        Act: Create CharmState from charm.
        Assert: InvalidCharmConfigError is raised with port error message.
        """
        # Arrange
        mock_charm = MagicMock()

        # Trigger actual ValidationError by trying to create invalid CharmConfig
        def raise_validation_error(config_class):
            return config_class(port=port)

        mock_charm.load_config.side_effect = raise_validation_error

        mock_loki_relation = MagicMock()
        mock_loki_relation.loki_endpoints = []

        # Act
        with pytest.raises(InvalidCharmConfigError) as exc_info:
            CharmState.from_charm(mock_charm, mock_loki_relation)

        # Assert
        assert "Invalid charm configuration: port" in str(exc_info.value)
        mock_charm.load_config.assert_called_once_with(CharmConfig)

    def test_from_charm_with_multiple_validation_errors(self):
        """Test CharmState.from_charm with validation errors.

        Arrange: Set up mock charm that raises ValidationError.
        Act: Create CharmState from charm.
        Assert: InvalidCharmConfigError is raised with port in error message.
        """
        # Arrange
        mock_charm = MagicMock()
        # Create a ValidationError with actual validation failure
        try:
            CharmConfig(port=0)  # This will raise ValidationError
        except ValidationError as e:
            mock_charm.load_config.side_effect = e

        mock_loki_relation = MagicMock()
        mock_loki_relation.loki_endpoints = []

        # Act
        with pytest.raises(InvalidCharmConfigError) as exc_info:
            CharmState.from_charm(mock_charm, mock_loki_relation)

        # Assert
        # Error message should contain the invalid configuration message
        error_msg = str(exc_info.value)
        assert "Invalid charm configuration:" in error_msg
        assert "port" in error_msg

    def test_from_charm_without_loki_endpoints(self):
        """Test CharmState.from_charm when loki endpoints are empty.

        Arrange: Set up mock charm without loki endpoints.
        Act: Create CharmState from charm.
        Assert: Loki endpoint fields have default values.
        """
        # Arrange
        mock_charm = MagicMock()
        mock_charm.load_config.return_value = CharmConfig(port=2801)

        mock_loki_relation = MagicMock()
        mock_loki_relation.loki_endpoints = []

        # Act
        state = CharmState.from_charm(mock_charm, mock_loki_relation)

        # Assert
        assert state.falcosidekick_loki_endpoint == "/loki/api/v1/push"
        assert state.falcosidekick_loki_hostport == ""
        assert state.falcosidekick_listenport == 2801
