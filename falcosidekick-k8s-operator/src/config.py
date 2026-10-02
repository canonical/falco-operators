# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm config option module."""

import logging

from pydantic import BaseModel, field_validator

logger = logging.getLogger(__name__)


class InvalidCharmConfigError(Exception):
    """Exception raised when the charm configuration is invalid."""


class CharmConfig(BaseModel):
    """The pydantic model for charm config.

    Note that the charm config should be loaded via ops.CharmBase.load_config().
    """

    port: int = 2801

    @field_validator("port")
    @classmethod
    def validate_port(cls, value: int) -> int:
        """Validate the port number.

        Args:
            value: The port input to validate.

        Returns:
            Valid port number for configuring Falcosidekick service.

        Raises:
            ValueError: If the port number is not in the valid range.
        """
        if not (1 <= value <= 65535):
            logger.error("Invalid port number: %d. Must be between 1 and 65535.", value)
            raise ValueError(f"Port number {value} is out of valid range [1-65535].")
        return value
