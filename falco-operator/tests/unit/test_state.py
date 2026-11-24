# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for Falco state module."""

from unittest.mock import patch

import ops
import ops.testing
import pytest
from pydantic import AnyUrl

from charm import Falco
from config import InvalidCharmConfigError


class TestCharmState:
    """Test CharmState class."""

    @patch("charm.FalcoService")
    def test_valid_charm_state(self, mock_service, mock_charm_dir, mock_falco_layout):
        """Test valid config cause no error when loading charm state."""
        context = ops.testing.Context(charm_type=Falco, charm_root=mock_charm_dir)
        state = ops.testing.State(
            config={
                "custom-config-repository": "git+ssh://git@github.com/canonical/falco-configs.git"
            }
        )

        with context(context.on.install(), state) as manager:
            charm = manager.charm
            state = charm.state  # trigger the load of state
            assert state.custom_config_repo == AnyUrl(
                "git+ssh://git@github.com/canonical/falco-configs.git"
            )
            assert state.custom_config_repo_ref == ""
            assert state.custom_config_repo_ssh_key is None
            assert state.custom_rules_follow_interval == "1h"

    @patch("charm.FalcoService")
    def test_valid_charm_state_with_tag(self, mock_service, mock_charm_dir, mock_falco_layout):
        """Test valid config cause no error when loading charm state."""
        context = ops.testing.Context(charm_type=Falco, charm_root=mock_charm_dir)
        state = ops.testing.State(
            config={
                "custom-config-repository": "git+ssh://git@github.com/canonical/falco-configs.git@main"
            }
        )

        with context(context.on.install(), state) as manager:
            charm = manager.charm
            state = charm.state  # trigger the load of state
            assert state.custom_config_repo == AnyUrl(
                "git+ssh://git@github.com/canonical/falco-configs.git"
            )
            assert state.custom_config_repo_ref == "main"
            assert state.custom_config_repo_ssh_key is None

    @patch("charm.FalcoService")
    def test_invalid_charm_state(self, mock_service, mock_charm_dir, mock_falco_layout):
        """Test invalid config causing error when loading charm state."""
        context = ops.testing.Context(charm_type=Falco, charm_root=mock_charm_dir)
        state = ops.testing.State(config={"custom-config-repository": "Not a URL"})

        with context(context.on.install(), state) as manager:
            charm = manager.charm
            with pytest.raises(InvalidCharmConfigError):
                _ = charm.state  # trigger the load of state

    @patch("charm.FalcoService")
    def test_valid_charm_state_with_custom_rules_secret(
        self, mock_service, mock_charm_dir, mock_falco_layout
    ):
        """Test loading state from a custom rules secret."""
        secret_id = "secret:d5dn431kohtcgpn8ou4g"  # nosec B105 - test secret ID
        oci_ref = "quay.io/canonical/falco-rules:latest"
        context = ops.testing.Context(charm_type=Falco, charm_root=mock_charm_dir)
        state = ops.testing.State(
            config={"custom-rules-secret": secret_id},
            secrets=[
                ops.testing.Secret(
                    id=secret_id,
                    tracked_content={
                        "username": "robot",
                        "password": "token",
                        "oci_ref": oci_ref,
                    },
                )
            ],
        )

        with context(context.on.install(), state) as manager:
            charm_state = manager.charm.state
            assert charm_state.custom_rules is not None
            assert charm_state.custom_rules.username == "robot"
            assert charm_state.custom_rules.password == "token"  # nosec B105 - test credential
            assert charm_state.custom_rules.oci_ref == oci_ref

    @pytest.mark.parametrize(
        ("secret_content", "error"),
        [
            ({"other": "value"}, "username: Field required"),
            ({"username": "robot", "password": "token"}, "oci_ref: Field required"),
            (
                {"password": "token", "oci_ref": "quay.io/org/rules:latest"},
                "username: Field required",
            ),
            (
                {"username": "robot", "oci_ref": "quay.io/org/rules:latest"},
                "password: Field required",
            ),
            (
                {"username": "robot", "password": "", "oci_ref": "quay.io/org/rules:latest"},
                "at least 1 character",
            ),
            (
                {
                    "username": "robot",
                    "password": "token",
                    "oci_ref": "https://quay.io/org/rules:latest",
                },
                "must not include a URL scheme",
            ),
        ],
    )
    @patch("charm.FalcoService")
    def test_invalid_custom_rules_secret(
        self, mock_service, secret_content, error, mock_charm_dir, mock_falco_layout
    ):
        """Test validation of the custom rules secret payload."""
        secret_id = "secret:d5dn431kohtcgpn8ou4g"  # nosec B105 - test secret ID
        context = ops.testing.Context(charm_type=Falco, charm_root=mock_charm_dir)
        state = ops.testing.State(
            config={"custom-rules-secret": secret_id},
            secrets=[ops.testing.Secret(id=secret_id, tracked_content=secret_content)],
        )

        with context(context.on.install(), state) as manager:
            charm = manager.charm
            with pytest.raises(InvalidCharmConfigError, match=error):
                _ = charm.state
