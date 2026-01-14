# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm state module."""

import itertools
import logging
from abc import ABC, abstractmethod
from typing import Optional

import ops
from charms.loki_k8s.v1.loki_push_api import LokiPushApiConsumer
from pydantic import BaseModel, HttpUrl, ValidationError

from certificates import TlsCertificateRequirer
from config import CharmConfig, InvalidCharmConfigError

logger = logging.getLogger(__name__)

TlsHealthcheckPort = 2810  # Falcosidekick TLS healthcheck port (hardcoded)


class CharmState(BaseModel):
    """The pydantic model for charm state.

    This model represents the runtime state of the charm, derived from
    the charm configuration and other sources.

    Attributes:
        falcosidekick_listenport: The port on which Falcosidekick listens.
        falcosidekick_loki_endpoint: The URL of the Loki push API endpoint.
        falcosidekick_loki_hostport: The host and port of the Loki push API endpoint.
        falcosidekick_tlsserver_key_file: The file path to the TLS server private key.
        falcosidekick_tlsserver_cert_file: The file path to the TLS server certificate.
        falcosidekick_tlsserver_notlsport: The port for non-TLS connections (for health check only).
        ca_cert: The CA certificate content for TLS verification.
    """

    falcosidekick_listenport: int
    falcosidekick_loki_endpoint: str
    falcosidekick_loki_hostport: str
    falcosidekick_tlsserver_key_file: str
    falcosidekick_tlsserver_cert_file: str
    falcosidekick_tlsserver_notlsport: int
    ca_cert: str

    @classmethod
    def from_charm(
        cls,
        charm: ops.CharmBase,
        loki_push_api_consumer: LokiPushApiConsumer,
        tls_certificate_requirer: TlsCertificateRequirer,
    ) -> "CharmState":
        """Create a CharmState from a charm instance.

        Loads and validates the charm configuration, then constructs a CharmState
        object from the validated configuration.

        Args:
            charm: The charm instance from which to extract state.
            loki_push_api_consumer: The LokiPushApiConsumer instance to get Loki relation data.
            tls_certificate_requirer: The TlsCertificateRequirer instance to get TLS data.

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
            certificate_ready = tls_certificate_requirer.is_ready()
            private_key_file = ""
            certificate_file = ""
            notlsport = charm_config.port  # default to listenport
            if certificate_ready:
                private_key_file = tls_certificate_requirer.private_key_name
                certificate_file = tls_certificate_requirer.certificate_name
                notlsport = TlsHealthcheckPort  # Falcosidekick TLS healthcheck port (hardcoded)
        except ValidationError as e:
            logger.error("Configuration validation error: %s", e)
            error_fields = set(itertools.chain.from_iterable(err["loc"] for err in e.errors()))
            error_field_str = " ".join(f"{f}" for f in error_fields)
            raise InvalidCharmConfigError(f"Invalid charm configuration: {error_field_str}") from e
        return cls(
            falcosidekick_listenport=charm_config.port,
            falcosidekick_loki_endpoint=loki_endpoint,
            falcosidekick_loki_hostport=loki_hostport,
            falcosidekick_tlsserver_key_file=private_key_file,
            falcosidekick_tlsserver_cert_file=certificate_file,
            falcosidekick_tlsserver_notlsport=notlsport,
            ca_cert=tls_certificate_requirer.get_ca_cert(),
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
