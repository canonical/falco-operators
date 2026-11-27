# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm config option module."""

import logging
import re
from decimal import Decimal
from typing import Optional

from ops import Secret
from pydantic import AnyUrl, BaseModel, ConfigDict, field_validator

SUPPORTED_SCHEMES = "git+ssh"

DEFAULT_FOLLOW_INTERVAL = "1h"
# Matches one <number><unit> part. The validator requires the matches to cover the
# whole string, so this pattern both validates and extracts the interval parts.
FOLLOW_INTERVAL_PATTERN = re.compile(r"(?P<number>\d+(?:\.\d+)?)(?P<unit>[smh])")
MAX_GO_DURATION_NS = Decimal(2**63 - 1)
MIN_FOLLOW_INTERVAL = "5m"
logger = logging.getLogger(__name__)


def validate_oci_reference(value: str) -> str:
    """Validate a full OCI artifact reference.

    Args:
        value: OCI artifact reference.

    Returns:
        The validated reference.

    Raises:
        ValueError: If the reference is not a full OCI reference.
    """
    if "://" in value:
        raise ValueError("must not include a URL scheme")
    if "/" not in value:
        raise ValueError("must include a registry and repository")
    if any(character.isspace() for character in value):
        raise ValueError("must not include whitespace")
    return value


def duration_to_ns(value: str) -> Decimal:
    """Convert a Go duration string to nanoseconds.

    Args:
        value: A Go duration such as "30m" or "1h30m".

    Returns:
        The duration in nanoseconds.

    Raises:
        ValueError: If the value is not a valid Go duration.
    """
    matches = list(FOLLOW_INTERVAL_PATTERN.finditer(value))
    if not matches or "".join(match.group(0) for match in matches) != value:
        raise ValueError("must be a Go duration such as '30m' or '1h'")
    unit_seconds = {"s": 1, "m": 60, "h": 3600}
    return sum(
        (
            Decimal(match.group("number")) * unit_seconds[match.group("unit")] * 1_000_000_000
            for match in matches
        ),
        start=Decimal(0),
    )


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
        custom_rules_refresh_interval (str): How often falcoctl checks for OCI rules updates.
    """

    # Pydantic model config
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Charm Configs
    custom_config_repository: Optional[AnyUrl] = None
    custom_config_repo_ssh_key: Optional[Secret] = None
    custom_rules_secret: Optional[Secret] = None
    custom_rules_refresh_interval: str = DEFAULT_FOLLOW_INTERVAL

    @field_validator("custom_rules_refresh_interval")
    @classmethod
    def validate_custom_rules_refresh_interval(cls, value: str) -> str:
        """Validate the custom rules refresh interval.

        Args:
            value: The configured refresh interval.

        Returns:
            The validated interval.

        Raises:
            ValueError: If the interval is invalid, below the minimum, or beyond Go's
                duration range.
        """
        total_ns = duration_to_ns(value)
        if total_ns < duration_to_ns(MIN_FOLLOW_INTERVAL):
            raise ValueError(
                f"custom_rules_refresh_interval must be at least {MIN_FOLLOW_INTERVAL}"
            )
        if total_ns > MAX_GO_DURATION_NS:
            raise ValueError("custom_rules_refresh_interval is too large for a Go duration")
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
