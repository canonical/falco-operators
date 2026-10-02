# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm config option module."""

import logging
from typing import Optional

from ops import Secret
from pydantic import AnyUrl, BaseModel, ConfigDict, field_validator

SUPPORTED_SCHEMES = "git+ssh"
logger = logging.getLogger(__name__)


class InvalidCharmConfigError(Exception):
    """Exception raised when the charm configuration is invalid."""


class CharmConfig(BaseModel):
    """The pydantic model for charm config.

    Note that the charm config should be loaded via ops.CharmBase.load_config().

    Attributes:
        custom_config_ssh_key (Secret): Optional SSH key for custom configuration repository.
        custom_config_repository (AnyUrl): Optional URL to a custom configuration repository.
    """

    # Pydantic model config
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Charm Configs
    custom_config_repository: Optional[AnyUrl] = None
    custom_config_repo_ssh_key: Optional[Secret] = None

    @field_validator("custom_config_repository")
    @classmethod
    def validate_custom_config_repository(cls, repo: Optional[AnyUrl]) -> Optional[AnyUrl]:
        """Validate the custom configuration repository URL.

        Args:
            repo: The custom configuration repository URL.

        Returns:
            The validated URL or None.

        Raises:
            InvalidCharmConfigError: If the URL scheme is unsupported or username is missing.
        """
        if repo is None:
            return None

        if repo.scheme not in SUPPORTED_SCHEMES:
            err_msg = f"Unsupported URL scheme '{repo.scheme}' in custom_config_repository"
            logger.error(err_msg)
            raise InvalidCharmConfigError(err_msg)

        if not repo.username:
            err_msg = "Username missing in custom_config_repository URL"
            logger.error(err_msg)
            raise InvalidCharmConfigError(err_msg)

        return repo
