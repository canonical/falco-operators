# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm state module."""

import itertools
import logging
from abc import ABC, abstractmethod
from typing import Optional

import ops
from charmlibs.interfaces.http_endpoint import HttpEndpointRequirer
from pydantic import AnyUrl, BaseModel, ValidationError

from certificate import CertificateTransferRequirer
from config import CharmConfig, InvalidCharmConfigError

logger = logging.getLogger(__name__)


class CaCertificateRequiredError(Exception):
    """Exception raised when CA certificate is required but not provided."""


class CharmState(BaseModel):
    """The pydantic model for charm state.

    Attributes:
        custom_config_repo: Optional URL to a custom configuration repository.
        custom_config_repo_ref: Optional branch or tag to a custom configuration repository.
        custom_config_repo_ssh_key: Optional SSH key for custom configuration repository.
        http_output: Optional HTTP output data from http-output relation.
        ca_certs: A dictionary mapping relation IDs to sets of CA certificates from certificate-transfer relations.
    """

    custom_config_repo: Optional[AnyUrl] = None
    custom_config_repo_ref: Optional[str] = None
    custom_config_repo_ssh_key: Optional[str] = None
    http_output: Optional[dict[str, str]] = None
    ca_certs: dict[int, set[str]] = {}

    @classmethod
    def from_charm(
        cls,
        charm: ops.CharmBase,
        http_endpoint_requirer: HttpEndpointRequirer,
        cert_transfer_requirer: CertificateTransferRequirer,
    ) -> "CharmState":
        """Create a CharmState from a charm instance.

        Args:
            charm: The charm instance.
            http_endpoint_requirer: The HttpEndpointRequirer instance to get http output URL.
            cert_transfer_requirer: The CertificateTransferRequirer instance to get ca certificate.

        Returns:
            A CharmState instance.

        Raises:
            InvalidCharmConfigError: If configuration validation fails.
            CaCertificateRequiredError: If CA certificate is required but not provided.
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

        http_output = {}
        app_urls = http_endpoint_requirer.get_app_urls()
        for url in app_urls.values():
            # There should only be one URL since this relation is limited to 1, but if there are
            # multiple, just take the last one.
            http_output.update({"url": url})
            logger.info("Retrieved url info from relation: %s", url)

        ca_certs = cert_transfer_requirer.get_transferred_ca_cert()

        if "https" in http_output.get("url", "") and not cert_transfer_requirer.is_created():
            err_msg = "CA certificate is required for HTTPS endpoint"
            logger.error(err_msg)
            raise CaCertificateRequiredError(err_msg)

        return cls(
            custom_config_repo=custom_config_repo,
            custom_config_repo_ref=custom_config_repo_ref,
            custom_config_repo_ssh_key=custom_config_repo_ssh_key,
            http_output=http_output,
            ca_certs=ca_certs,
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
