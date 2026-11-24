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
from state import CustomRulesSecret


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
        oci_ref = "quay.io/canonical/falco-rules:latest"
        secret = ops.testing.Secret(
            tracked_content={
                "username": "robot",
                "password": "token",
                "oci_ref": oci_ref,
            }
        )
        context = ops.testing.Context(charm_type=Falco, charm_root=mock_charm_dir)
        state = ops.testing.State(
            config={"custom-rules-secret": secret.id},
            secrets=[secret],
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
        secret = ops.testing.Secret(tracked_content=secret_content)
        context = ops.testing.Context(charm_type=Falco, charm_root=mock_charm_dir)
        state = ops.testing.State(
            config={"custom-rules-secret": secret.id},
            secrets=[secret],
        )

        with context(context.on.install(), state) as manager:
            charm = manager.charm
            with pytest.raises(InvalidCharmConfigError, match=error):
                _ = charm.state

    def test_custom_rules_secret_repr_hides_values(self):
        """Test that the secret representation does not expose its values."""
        secret = CustomRulesSecret(
            username="robot",
            password="token",  # nosec B106 - test credential
            oci_ref="quay.io/private/rules:latest",
        )

        representation = repr(secret)
        assert "robot" not in representation
        assert "token" not in representation
        assert "quay.io" not in representation

    @patch("charm.FalcoService")
    def test_invalid_custom_rules_secret_does_not_expose_values(
        self, mock_service, mock_charm_dir, mock_falco_layout
    ):
        """Test that validation errors do not include secret values."""
        password = "super-secret-token"  # nosec B105 - test credential
        oci_ref = "https://quay.io/private/rules:latest"
        secret = ops.testing.Secret(
            tracked_content={
                "username": "robot",
                "password": password,
                "oci_ref": oci_ref,
            }
        )
        context = ops.testing.Context(charm_type=Falco, charm_root=mock_charm_dir)
        state = ops.testing.State(
            config={"custom-rules-secret": secret.id},
            secrets=[secret],
        )

        with (
            context(context.on.install(), state) as manager,
            pytest.raises(InvalidCharmConfigError) as exc_info,
        ):
            _ = manager.charm.state

        message = str(exc_info.value)
        assert "robot" not in message
        assert password not in message
        assert oci_ref not in message
        assert exc_info.value.__cause__ is None
        assert exc_info.value.__suppress_context__
