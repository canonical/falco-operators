# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm state module."""

import itertools
import json
import logging
from abc import ABC, abstractmethod
from typing import Optional

import ops
from pfe.interfaces.falcosidekick_http_endpoint import HttpEndpointRequirer
from pydantic import AnyUrl, BaseModel, ValidationError

from config import (
    DEFAULT_FOLLOW_INTERVAL,
    CharmConfig,
    ConflictingRulesSourceError,
    InvalidCharmConfigError,
)

logger = logging.getLogger(__name__)


class CharmState(BaseModel):
    """The pydantic model for charm state.

    Attributes:
        custom_config_repo: Optional URL to a custom configuration repository.
        custom_config_repo_ref: Optional branch or tag to a custom configuration repository.
        custom_config_repo_ssh_key: Optional SSH key for custom configuration repository.
        custom_rules_username: Optional OCI registry username for custom rules.
        custom_rules_password: Optional OCI registry password for custom rules.
        custom_rules_oci_ref: Optional OCI artifact reference for custom rules.
        custom_rules_follow_interval: How often falcoctl checks for OCI rules updates.
        http_output: Optional HTTP output data from http-output relation.
    """

    custom_config_repo: Optional[AnyUrl] = None
    custom_config_repo_ref: Optional[str] = None
    custom_config_repo_ssh_key: Optional[str] = None
    custom_rules_username: Optional[str] = None
    custom_rules_password: Optional[str] = None
    custom_rules_oci_ref: Optional[str] = None
    custom_rules_follow_interval: str = DEFAULT_FOLLOW_INTERVAL
    http_output: Optional[dict[str, str]] = None

    @classmethod
    def from_charm(
        cls, charm: ops.CharmBase, http_endpoint_requirer: HttpEndpointRequirer
    ) -> "CharmState":
        """Create a CharmState from a charm instance.

        Args:
            charm: The charm instance.
            http_endpoint_requirer: The HttpEndpointRequirer instance to get http output URL.

        Returns:
            A CharmState instance.

        Raises:
            InvalidCharmConfigError: If configuration validation fails.
        """
        try:
            charm_config = charm.load_config(CharmConfig)
        except ValidationError as e:
            logger.error("Configuration validation error: %s", e)
            error_fields = set(itertools.chain.from_iterable(err["loc"] for err in e.errors()))
            error_field_str = " ".join(f"{f}" for f in error_fields)
            raise InvalidCharmConfigError(f"Invalid charm configuration {error_field_str}") from e

        repo = charm_config.custom_config_repository
        custom_config_repo = None
        custom_config_repo_ref = None
        if repo is not None:
            path, *ref_string = repo.path.split(sep="@", maxsplit=1)
            username = f"{repo.username}@" if isinstance(repo.username, str) else ""
            custom_config_repo = AnyUrl(f"{repo.scheme}://{username}{repo.host}{path}")
            custom_config_repo_ref = ref_string[0] if ref_string else ""

        custom_config_repo_ssh_key = _fetch_custom_ssh_key(charm.model, charm_config)
        custom_rules = _fetch_custom_rules_secret(charm.model, charm_config)

        if custom_config_repo and custom_rules:
            raise ConflictingRulesSourceError(
                "Only one of custom-config-repository and custom-rules-secret can be configured"
            )

        http_output = {}
        app_urls = http_endpoint_requirer.get_app_urls()
        for url in app_urls.values():
            # There should only be one URL since this relation is limited to 1, but if there are
            # multiple, just take the last one.
            http_output.update({"url": url})
            logger.info("Retrieved url info from relation: %s", url)

        return cls(
            custom_config_repo=custom_config_repo,
            custom_config_repo_ref=custom_config_repo_ref,
            custom_config_repo_ssh_key=custom_config_repo_ssh_key,
            custom_rules_username=custom_rules[0] if custom_rules else None,
            custom_rules_password=custom_rules[1] if custom_rules else None,
            custom_rules_oci_ref=custom_rules[2] if custom_rules else None,
            custom_rules_follow_interval=charm_config.custom_rules_follow_interval,
            http_output=http_output,
        )


class CharmBaseWithState(ops.CharmBase, ABC):
    """The CharmBase than can build a CharmState."""

    @property
    @abstractmethod
    def state(self) -> CharmState | None:
        """The charm state."""

    @abstractmethod
    def reconcile(self, _: ops.HookEvent) -> None:
        """Reconcile configuration."""


def _fetch_custom_ssh_key(model: ops.Model, config: CharmConfig) -> Optional[str]:
    """Fetch the custom SSH key from the charm config.

    Args:
        model: The ops model.
        config: The charm config

    Returns:
        The SSH key as a string, or None if not found.

    Raises:
        InvalidCharmConfigError: If the secret cannot be accessed properly.
    """
    if not config.custom_config_repo_ssh_key:
        return None

    try:
        ssh_key_id = config.custom_config_repo_ssh_key.id
        ssh_key_secret = model.get_secret(id=ssh_key_id)
    except ops.SecretNotFoundError as exc:
        raise InvalidCharmConfigError("Repository secret not found.") from exc

    ssh_key_content = ssh_key_secret.get_content(refresh=True).get("value")

    if not ssh_key_content:
        raise InvalidCharmConfigError(
            "Repository secret is empty or does not contain the expected key 'value'."
        )
    return ssh_key_content


def _fetch_custom_rules_secret(
    model: ops.Model, config: CharmConfig
) -> Optional[tuple[str, str, str]]:
    """Fetch OCI registry credentials and artifact reference from the charm config.

    Args:
        model: The Juju model.
        config: The charm config.

    Returns:
        A tuple with the username, password, and OCI reference, or None if not configured.

    Raises:
        InvalidCharmConfigError: If the secret cannot be accessed or is missing required keys.
    """
    if not config.custom_rules_secret:
        return None

    try:
        secret = model.get_secret(id=config.custom_rules_secret.id)
        content = secret.get_content(refresh=True)
    except ops.SecretNotFoundError as exc:
        raise InvalidCharmConfigError("Custom rules secret not found.") from exc

    raw_value = content.get("value")
    if not raw_value:
        raise InvalidCharmConfigError(
            "Custom rules secret must contain a 'value' key with a JSON object."
        )

    try:
        rules_config = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise InvalidCharmConfigError(
            "Custom rules secret 'value' must be a valid JSON object."
        ) from exc

    if not isinstance(rules_config, dict):
        raise InvalidCharmConfigError("Custom rules secret 'value' must be a JSON object.")

    required_keys = ("username", "password", "oci_ref")
    missing_keys = [key for key in required_keys if not rules_config.get(key)]
    if missing_keys:
        raise InvalidCharmConfigError(
            "Custom rules secret JSON is missing required keys: " + ", ".join(missing_keys)
        )
    if not all(isinstance(rules_config[key], str) for key in required_keys):
        raise InvalidCharmConfigError(
            "Custom rules secret JSON values for username, password, and oci_ref must be strings"
        )

    username = rules_config["username"]
    password = rules_config["password"]
    oci_ref = rules_config["oci_ref"]

    if "://" in oci_ref or "/" not in oci_ref:
        raise InvalidCharmConfigError(
            "Custom rules secret key 'oci_ref' must be a full OCI reference without a URL scheme"
        )

    return username, password, oci_ref
