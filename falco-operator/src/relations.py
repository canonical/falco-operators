# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm relations module."""

import logging
from typing import Optional

import ops
from charmlibs.interfaces.http_endpoint import HttpEndpointDataModel, HttpEndpointRequirer

logger = logging.getLogger(__name__)


class HttpEndpointManager:
    """Manager for HTTP output relation.

    This class manages requirer side of the http_endpoint interface, retrieving the leader's
    address and listening port from related units.
    """

    def __init__(self, charm: ops.CharmBase, relation_name: str) -> None:
        """Initialize http output relation requirer.

        Args:
            charm: charm instance.
            relation_name: http_output relation name.
        """
        self._charm = charm
        self._relation_name = relation_name
        self._endpoint_requirer = HttpEndpointRequirer(charm, relation_name=relation_name)

    def get_http_endpoint(self) -> Optional[HttpEndpointDataModel]:
        """Get http endpoints info from relation.

        Returns:
            The endpoint info as a HttpEndpointDataModel, or None if not available.
        """
        endpoints = self._endpoint_requirer.http_endpoints
        if not endpoints:
            logger.warning("Relation data (%s) is not ready", self._relation_name)
            return None

        # Limit to only 1 relation, see charmcraft.yaml
        endpoint = endpoints[0]
        if endpoint.url is None:
            logger.error("Relation data (%s) is missing URL", self._relation_name)
            return None

        logger.info("Retrieved HTTP output info from relation: %s", endpoint.model_dump())
        return endpoint
