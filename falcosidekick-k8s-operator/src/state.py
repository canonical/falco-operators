# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm state module."""

import itertools
import logging
from abc import ABC, abstractmethod

import ops
from pydantic import BaseModel, ValidationError

from config import CharmConfig, InvalidCharmConfigError

logger = logging.getLogger(__name__)


class CharmState(BaseModel):
    """The pydantic model for charm state.

    This model represents the runtime state of the charm, derived from
    the charm configuration and other sources.

    Attributes:
        falcosidekick_listenport: The port on which Falcosidekick listens.
    """

    falcosidekick_listenport: int

    @classmethod
    def from_charm(cls, charm: ops.CharmBase) -> "CharmState":
        """Create a CharmState from a charm instance.

        Loads and validates the charm configuration, then constructs a CharmState
        object from the validated configuration.

        Args:
            charm: The charm instance from which to extract state.

        Returns:
            CharmState: A validated CharmState instance.

        Raises:
            InvalidCharmConfigError: If configuration validation fails.
        """
        try:
            charm_config = charm.load_config(CharmConfig)
        except ValidationError as e:
            logger.error("Configuration validation error: %s", e)
            error_fields = set(itertools.chain.from_iterable(err["loc"] for err in e.errors()))
            error_field_str = " ".join(f"{f}" for f in error_fields)
            raise InvalidCharmConfigError(f"Invalid charm configuration: {error_field_str}") from e

        return cls(falcosidekick_listenport=charm_config.port)


class CharmBaseWithState(ops.CharmBase, ABC):
    """Base class for charms that maintain state.

    This abstract base class extends ops.CharmBase to provide state management
    capabilities through the CharmState model.
    """

    @property
    @abstractmethod
    def state(self) -> CharmState | None:
        """Get the charm state.

        Returns:
            The current charm state, or None if not initialized.
        """

    @abstractmethod
    def reconcile(self, _: ops.HookEvent) -> None:
        """Reconcile configuration.

        Ensures the charm's workload and configuration are in the desired state.

        Args:
            _: The hook event that triggered reconciliation.
        """
