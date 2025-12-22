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
        """Test creating a CharmState instance."""
        state = CharmState(falcosidekick_listenport=8080)
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
        """Test CharmState.from_charm with valid configuration."""
        # Arrange
        mock_charm = MagicMock()
        mock_charm.load_config.return_value = CharmConfig(port=port)

        # Act
        state = CharmState.from_charm(mock_charm)

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
        """Test CharmState.from_charm with invalid configuration."""
        # Arrange
        mock_charm = MagicMock()

        # Trigger actual ValidationError by trying to create invalid CharmConfig
        def raise_validation_error(config_class):
            return config_class(port=port)

        mock_charm.load_config.side_effect = raise_validation_error

        # Act
        with pytest.raises(InvalidCharmConfigError) as exc_info:
            CharmState.from_charm(mock_charm)

        # Assert
        assert "Invalid charm configuration: port" in str(exc_info.value)
        mock_charm.load_config.assert_called_once_with(CharmConfig)

    def test_from_charm_with_multiple_validation_errors(self):
        """Test CharmState.from_charm with validation errors."""
        # Arrange
        mock_charm = MagicMock()
        # Create a ValidationError with actual validation failure
        try:
            CharmConfig(port=0)  # This will raise ValidationError
        except ValidationError as e:
            mock_charm.load_config.side_effect = e

        # Act
        with pytest.raises(InvalidCharmConfigError) as exc_info:
            CharmState.from_charm(mock_charm)

        # Assert
        # Error message should contain the invalid configuration message
        error_msg = str(exc_info.value)
        assert "Invalid charm configuration:" in error_msg
        assert "port" in error_msg
