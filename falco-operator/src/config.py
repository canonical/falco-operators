# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm config option module."""

import logging
import re
from typing import Optional

from ops import Secret
from pydantic import AnyUrl, BaseModel, ConfigDict, field_validator

SUPPORTED_SCHEMES = "git+ssh"
DEFAULT_FOLLOW_INTERVAL = "1h"
FOLLOW_INTERVAL_PATTERN = re.compile(r"^(?:\d+(?:\.\d+)?(?:s|m|h))+$")
logger = logging.getLogger(__name__)


class InvalidCharmConfigError(Exception):
    """Exception raised when the charm configuration is invalid."""


class ConflictingRulesSourceError(InvalidCharmConfigError):
    """Exception raised when more than one custom rules source is configured."""


class CharmConfig(BaseModel):
    """The pydantic model for charm config.

    Note that the charm config should be loaded via ops.CharmBase.load_config().

    Attributes:
        custom_config_ssh_key (Secret): Optional SSH key for custom configuration repository.
        custom_config_repository (AnyUrl): Optional URL to a custom configuration repository.
        custom_rules_secret (Secret): Optional secret with OCI registry credentials and rules reference.
        custom_rules_follow_interval (str): How often falcoctl checks for OCI rules updates.
    """

    # Pydantic model config
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Charm Configs
    custom_config_repository: Optional[AnyUrl] = None
    custom_config_repo_ssh_key: Optional[Secret] = None
    custom_rules_secret: Optional[Secret] = None
    custom_rules_follow_interval: str = DEFAULT_FOLLOW_INTERVAL

    @field_validator("custom_rules_follow_interval")
    @classmethod
    def validate_custom_rules_follow_interval(cls, value: str) -> str:
        """Validate the falcoctl follow interval.

        Args:
            value: The configured follow interval.

        Returns:
            The validated interval, or the default interval for an empty value.

        Raises:
            ValueError: If the interval is not a valid Go duration.
        """
        if value == "":
            return DEFAULT_FOLLOW_INTERVAL
        if not FOLLOW_INTERVAL_PATTERN.fullmatch(value):
            raise ValueError(
                "custom_rules_follow_interval must be a Go duration such as '30m' or '1h'"
            )
        return value

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
