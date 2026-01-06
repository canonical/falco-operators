# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm state module."""

import itertools
import logging
from abc import ABC, abstractmethod

import ops
from pydantic import BaseModel, ValidationError

from config import CharmConfig, InvalidCharmConfigError
from relations import InvalidLokiRelationError, LokiRelationManager

logger = logging.getLogger(__name__)


class InvalidStateError(Exception):
    """Exception raised when a charm configuration is invalid and unrecoverable."""


class CharmState(BaseModel):
    """The pydantic model for charm state.

    This model represents the runtime state of the charm, derived from
    the charm configuration and other sources.

    Attributes:
        falcosidekick_listenport: The port on which Falcosidekick listens.
        loki_endpoint_url: The URL of the Loki endpoint, if available.
    """

    falcosidekick_listenport: int
    falcosidekick_loki_endpoint: str
    falcosidekick_loki_hostport: str

    @classmethod
    def from_charm(
        cls,
        charm: ops.CharmBase,
        loki_relation: LokiRelationManager,
    ) -> "CharmState":
        """Create a CharmState from a charm instance.

        Loads and validates the charm configuration, then constructs a CharmState
        object from the validated configuration.

        Args:
            charm: The charm instance from which to extract state.
            loki_relation: The LokiRelationManager instance to get Loki relation data.

        Returns:
            CharmState: A validated CharmState instance.

        Raises:
            InvalidCharmConfigError: If configuration validation fails.
            InvalidStateError: If relation data is invalid.
        """
        try:
            charm_config = charm.load_config(CharmConfig)
            _url = loki_relation.get_loki_http_url()
            loki_endpoint = _url.path if _url else "/loki/api/v1/push"
            loki_hostport = f"{_url.scheme}://{_url.host}:{_url.port}" if _url else ""
        except ValidationError as e:
            logger.error("Configuration validation error: %s", e)
            error_fields = set(itertools.chain.from_iterable(err["loc"] for err in e.errors()))
            error_field_str = " ".join(f"{f}" for f in error_fields)
            raise InvalidCharmConfigError(f"Invalid charm configuration: {error_field_str}") from e
        except InvalidLokiRelationError as e:
            logger.error("Loki relation data validation error: %s", e)
            raise InvalidStateError("Invalid Loki relation data") from e
        return cls(
            falcosidekick_listenport=charm_config.port,
            falcosidekick_loki_endpoint=loki_endpoint,
            falcosidekick_loki_hostport=loki_hostport,
        )


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
