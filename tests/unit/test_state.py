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
