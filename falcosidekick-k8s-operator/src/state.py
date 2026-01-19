# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm state module."""

import itertools
import logging
from abc import ABC, abstractmethod
from typing import Optional

import ops
from charms.loki_k8s.v1.loki_push_api import LokiPushApiConsumer
from charms.traefik_k8s.v2.ingress import IngressPerAppRequirer
from pydantic import BaseModel, HttpUrl, ValidationError

from config import CharmConfig, InvalidCharmConfigError

logger = logging.getLogger(__name__)


class CharmState(BaseModel):
    """The pydantic model for charm state.

    This model represents the runtime state of the charm, derived from
    the charm configuration and other sources.

    Attributes:
        enable_tls: Whether TLS is enabled for the Falcosidekick workload.
        http_endpoint_config: The HTTP endpoint configuration dictionary.
        falcosidekick_listenport: The port on which Falcosidekick listens.
        falcosidekick_loki_endpoint: The URL of the Loki push API endpoint.
        falcosidekick_loki_hostport: The host and port of the Loki push API endpoint.
    """

    enable_tls: bool
    http_endpoint_config: dict
    falcosidekick_listenport: int
    falcosidekick_loki_endpoint: str
    falcosidekick_loki_hostport: str

    @classmethod
    def from_charm(
        cls,
        charm: ops.CharmBase,
        loki_push_api_consumer: LokiPushApiConsumer,
        ingress_requirer: IngressPerAppRequirer,
    ) -> "CharmState":
        """Create a CharmState from a charm instance.

        Loads and validates the charm configuration, then constructs a CharmState
        object from the validated configuration.

        Args:
            charm: The charm instance from which to extract state.
            loki_push_api_consumer: The LokiPushApiConsumer instance to get Loki relation data.
            ingress_requirer: The IngressPerAppRequirer instance to get ingress relation data.

        Returns:
            CharmState: A validated CharmState instance.

        Raises:
            InvalidCharmConfigError: If configuration validation fails.
            InvalidStateError: If relation data is invalid.
        """
        try:
            charm_config = charm.load_config(CharmConfig)
            _url = _get_loki_ingress_endpoint(loki_push_api_consumer)
            loki_endpoint = _url.path if _url and _url.path else "/loki/api/v1/push"
            loki_hostport = f"{_url.scheme}://{_url.host}:{_url.port}" if _url else ""
            enable_tls = True
            http_endpoint_config = {
                "path": "/",
                "scheme": "https",
                "set_ports": True,
                "hostname": None,
                "listen_port": charm_config.port,
            }
            if ingress_requirer.is_ready():
                ingress_url = HttpUrl(ingress_requirer.url)
                enable_tls = False  # TLS is handled by ingress
                http_endpoint_config.update(
                    {
                        "path": ingress_url.path,
                        "scheme": ingress_url.scheme,
                        "set_ports": False,
                        "hostname": ingress_url.host,
                        "listen_port": ingress_url.port,
                    }
                )
        except ValidationError as e:
            logger.error("Configuration validation error: %s", e)
            error_fields = set(itertools.chain.from_iterable(err["loc"] for err in e.errors()))
            error_field_str = " ".join(f"{f}" for f in error_fields)
            raise InvalidCharmConfigError(f"Invalid charm configuration: {error_field_str}") from e
        return cls(
            enable_tls=enable_tls,
            http_endpoint_config=http_endpoint_config,
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


def _get_loki_ingress_endpoint(loki_push_api_consumer: LokiPushApiConsumer) -> Optional[HttpUrl]:
    """Get the first encounter Loki ingress endpoint.

    Args:
        loki_push_api_consumer: The LokiPushApiConsumer instance to get Loki relation data

    Returns:
        The first seen one Loki ingress endpoint in the relation data or None if not found.
    """
    try:
        for endpoint in loki_push_api_consumer.loki_endpoints:
            return HttpUrl(endpoint.get("url"))
    except ValidationError:
        logger.warning("Loki ingress endpoint not ready")

    return None
