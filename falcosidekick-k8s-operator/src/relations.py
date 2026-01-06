# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm relations module."""

import logging

import ops
from charms.loki_k8s.v1.loki_push_api import LokiPushApiConsumer
from pydantic import BaseModel, HttpUrl, ValidationError

logger = logging.getLogger(__name__)


class MissingLokiRelationError(Exception):
    """Exception raised when the Loki relation is missing."""


class InvalidLokiRelationError(Exception):
    """Exception raised for invalid Loki relation data."""


class HttpOutputDataBag(BaseModel):
    """Data bag model for HTTP output relation."""

    url: str


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


class HttpOutputProvider:
    """Http output relation provider.

    This class manages the http_output relation as a provider, publishing
    the leader's address and listening port for other charms to consume.
    """

    def __init__(self, charm: ops.CharmBase, relation_name: str) -> None:
        """Initialize http output relation provider.

        Args:
            charm: charm instance.
            relation_name: http_output relation name.
        """
        self._charm = charm
        self._relation_name = relation_name

    def set_http_output_info(self, port: int) -> None:
        """Set http output information to relations' application data bags.

        Args:
            port: The port on which Falcosidekick is listening.
        """
        if not self._charm.unit.is_leader():
            logger.debug("Only leader unit can set http output information")
            return

        relations = self._charm.model.relations[self._relation_name]
        if not relations:
            logger.debug(f"No {self._relation_name} relations found")
            return

        # Get the leader's address
        binding = self._charm.model.get_binding(self._relation_name)
        if not binding:
            logger.warning("Could not determine ingress address for http output relation")
            return

        ingress_address = binding.network.ingress_address
        if not ingress_address:
            logger.warning("Relation data (http-output) is not ready: missing ingress address")
            return

        scheme = "http"
        url = f"{scheme}://{ingress_address}:{port}"
        http_output = HttpOutputDataBag(url=url)

        # Publish the HTTP output to all relations' application data bags
        for relation in relations:
            relation_data = relation.data[self._charm.app]
            relation_data.update(http_output.model_dump())
            logger.info("Published HTTP output URL to relation %s: %s", relation.id, url)

        self._charm.unit.set_ports(port)
