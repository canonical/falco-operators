# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm relations module."""

import logging

import ops
from charmlibs.interfaces.http_endpoint import HttpEndpointProvider
from charms.loki_k8s.v1.loki_push_api import LokiPushApiConsumer
from pydantic import HttpUrl, ValidationError

logger = logging.getLogger(__name__)


class MissingLokiRelationError(Exception):
    """Exception raised when the Loki relation is missing."""


class InvalidLokiRelationError(Exception):
    """Exception raised for invalid Loki relation data."""


class LokiRelationManager:
    """Manager for Loki push API relation.

    This class manages the integration with Loki for log forwarding using the
    loki_push_api interface.
    """

    def __init__(self, charm: ops.CharmBase, relation_name: str) -> None:
        """Initialize the Loki relation manager.

        Args:
            charm: The charm instance that manages this relation.
            relation_name: The name of the relation endpoint.
        """
        self._charm = charm
        self._relation_name = relation_name
        self._loki_consumer = LokiPushApiConsumer(charm, relation_name=relation_name)

    def get_loki_http_url(self) -> HttpUrl | None:
        """Get one Loki push API endpoint url.

        Returns:
            The first seen one Loki endpoint URL in the relation data bag or None if not found.

        Raises:
            InvalidLokiRelationError: If the URL in the relation data bag is invalid.
        """
        endpoints = self._loki_consumer.loki_endpoints
        try:
            for endpoint in endpoints:
                if endpoint.get("url"):
                    return HttpUrl(endpoint["url"])
        except ValidationError as e:
            logger.error(f"Invalid URL in Loki endpoints databag: {e}")
            raise InvalidLokiRelationError from e

        return None


class HttpEndpointManager:
    """Manager for HTTP output relation.

    This class manages the provider side of http_endpoint interface, publishing the leader's
    address and listening port for other charms to consume.
    """

    def __init__(self, charm: ops.CharmBase, relation_name: str) -> None:
        """Initialize http endpoint relation provider.

        Args:
            charm: charm instance.
            relation_name: http_endpoint relation name.
        """
        self._charm = charm
        self._relation_name = relation_name
        self._endpoint_provider = HttpEndpointProvider(
            charm,
            relation_name=relation_name,
            scheme="http",  # default scheme
            listen_port=2801,  # default port
        )

    def set_scheme_and_listen_port(self, scheme: str, listen_port: int) -> None:
        """Set the scheme and listening port for the http endpoint.

        Args:
            scheme: The scheme to use (e.g., "http" or "https").
            listen_port: The port on which the service is listening.
        """
        self._endpoint_provider.set_scheme_and_listen_port(scheme, listen_port)
