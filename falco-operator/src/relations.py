# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm relations module."""

import logging
from typing import Optional

import ops
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class HttpOutputDataBag(BaseModel):
    """Data bag model for HTTP output relation."""

    url: str


class HttpOutputRequirer:
    """Http output relation requirer.

    This class manages the http_output relation as a requirer, consuming
    the HTTP output info from the http-output provider.
    """

    def __init__(self, charm: ops.CharmBase, relation_name: str) -> None:
        """Initialize http output relation requirer.

        Args:
            charm: charm instance.
            relation_name: http_output relation name.
        """
        self._charm = charm
        self._relation_name = relation_name

    def get_http_output_info(self) -> Optional[HttpOutputDataBag]:
        """Get http output info from relation.

        Returns:
            The HTTP output info as a HttpOutputDataBag, or None if not available.

        Raises:
            InvalidHttpOutputRelationError: If the URL in the relation data is invalid.
        """
        relations = self._charm.model.relations[self._relation_name]
        if not relations:
            logger.debug(f"No {self._relation_name} relations found")
            return None

        # Get the first relation encountered, as it is limited by only one relation (see
        # charmcraft.yaml). More than one relation should not exist.
        relation = relations[0]
        if relation.app is None:
            logger.debug("Related app is None")
            return None

        data = relation.data.get(relation.app)
        if not data:
            logger.warning("Relation data (http-output) is not ready")
            return None

        http_output = HttpOutputDataBag(**dict(data or {}))
        logger.info("Retrieved HTTP output info from relation: %s", http_output.model_dump())
        return http_output
