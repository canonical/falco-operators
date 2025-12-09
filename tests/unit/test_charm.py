# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for Falco charm."""

import shutil
from unittest.mock import MagicMock, patch

import ops
import ops.testing
import pytest
from pydantic import AnyUrl

from charm import Falco
from service import FalcoConfigurationError


class TestCharm:
    """Test Charm class."""

    @patch("charm.FalcoService")
    def test_charm_initialization(self, mock_service, mock_charm_dir, mock_falco_layout):
        """Test charm initialization."""
        context = ops.testing.Context(charm_type=Falco, charm_root=mock_charm_dir)
        state = ops.testing.State()

        with context(context.on.install(), state) as manager:
            charm = manager.charm
            assert charm.falco_layout is not None
            assert charm.falco_service_file is not None
            assert charm.managed_falco_config is not None

    def test_charm_initialization_missing_falco_directory(self, mock_charm_dir, mock_falco_layout):
        """Test charm initialization when Falco directory is missing."""
        context = ops.testing.Context(charm_type=Falco, charm_root=mock_charm_dir)
        state = ops.testing.State()

        # Remove the falco directory that was created by the fixture
        shutil.rmtree(mock_charm_dir / "falco")

        with pytest.raises(
            ops.testing.errors.UncaughtCharmError, match=r"ValueError.*does not exist"
        ):
            context.run(context.on.install(), state)

    @patch("charm.FalcoService")
    def test_on_install(self, mock_service_class, mock_charm_dir, mock_falco_layout):
        """Test the install event handler."""
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        context = ops.testing.Context(charm_type=Falco, charm_root=mock_charm_dir)
        state_in = ops.testing.State()
        state_out = context.run(context.on.install(), state_in)

        mock_service.install.assert_called_once()
        assert state_out.unit_status == ops.testing.MaintenanceStatus("Installing Falco service")

    @patch("charm.FalcoService")
    def test_on_install_fails_service_exception(
        self, mock_service_class, mock_charm_dir, mock_falco_layout
    ):
        """Test install event when service installation raises an exception."""
        mock_service = MagicMock()
        mock_service.install.side_effect = OSError("Install failed")
        mock_service_class.return_value = mock_service

        context = ops.testing.Context(charm_type=Falco, charm_root=mock_charm_dir)
        state_in = ops.testing.State()

        with pytest.raises(
            ops.testing.errors.UncaughtCharmError, match=r"OSError.*Install failed"
        ):
            context.run(context.on.install(), state_in)

        mock_service.install.assert_called_once()

    @patch("charm.FalcoService")
    def test_on_upgrade_charm(self, mock_service_class, mock_charm_dir, mock_falco_layout):
        """Test the upgrade_charm event handler."""
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        context = ops.testing.Context(charm_type=Falco, charm_root=mock_charm_dir)
        state_in = ops.testing.State()
        state_out = context.run(context.on.upgrade_charm(), state_in)

        mock_service.install.assert_called_once()
        assert state_out.unit_status == ops.testing.MaintenanceStatus("Installing Falco service")

    @patch("charm.FalcoService")
    def test_on_upgrade_fails_service_exception(
        self, mock_service_class, mock_charm_dir, mock_falco_layout
    ):
        """Test upgrade_charm event when service installation raises an exception."""
        mock_service = MagicMock()
        mock_service.install.side_effect = OSError("Upgrade failed")
        mock_service_class.return_value = mock_service

        context = ops.testing.Context(charm_type=Falco, charm_root=mock_charm_dir)
        state_in = ops.testing.State()

        with pytest.raises(
            ops.testing.errors.UncaughtCharmError, match=r"OSError.*Upgrade failed"
        ):
            context.run(context.on.upgrade_charm(), state_in)

        mock_service.install.assert_called_once()

    @patch("charm.FalcoService")
    def test_on_remove(self, mock_service_class, mock_charm_dir, mock_falco_layout):
        """Test the remove event handler."""
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        context = ops.testing.Context(charm_type=Falco, charm_root=mock_charm_dir)
        state_in = ops.testing.State()
        state_out = context.run(context.on.remove(), state_in)

        mock_service.remove.assert_called_once()
        assert state_out.unit_status == ops.testing.MaintenanceStatus("Removing Falco service")

    @patch("charm.FalcoService")
    def test_on_remove_fails_service_exception(
        self, mock_service_class, mock_charm_dir, mock_falco_layout
    ):
        """Test remove event when service removal raises an exception."""
        mock_service = MagicMock()
        mock_service.remove.side_effect = PermissionError("Cannot remove service")
        mock_service_class.return_value = mock_service

        context = ops.testing.Context(charm_type=Falco, charm_root=mock_charm_dir)
        state_in = ops.testing.State()

        with pytest.raises(
            ops.testing.errors.UncaughtCharmError, match=r"PermissionError.*Cannot remove service"
        ):
            context.run(context.on.remove(), state_in)

        mock_service.remove.assert_called_once()


class TestCharmConfigHandling:
    """Test charm configuration handling."""

    @patch("charm.FalcoService")
    def test_config_changed_with_custom_config_repository(
        self, mock_service_class, mock_charm_dir, mock_falco_layout
    ):
        """Test config_changed event with custom config repository configured."""
        mock_service = MagicMock()
        mock_service.check_active.return_value = True
        mock_service_class.return_value = mock_service

        context = ops.testing.Context(charm_type=Falco, charm_root=mock_charm_dir)
        state_in = ops.testing.State(
            config={"custom-config-repository": "git+ssh://github.com/user/repo.git"}
        )

        with context(context.on.config_changed(), state_in) as mgr:
            state = mgr.charm.state
            assert state.custom_config_repo == AnyUrl("git+ssh://github.com/user/repo.git")
            assert state.custom_config_repo_ref == ""
            state_out = mgr.run()
            mock_service.configure.assert_called_once()
            assert state_out.unit_status == ops.testing.ActiveStatus()

    @patch("charm.FalcoService")
    def test_config_changed_with_custom_config_repository_and_ref(
        self, mock_service_class, mock_charm_dir, mock_falco_layout
    ):
        """Test config_changed event with custom config repository and ref configured."""
        mock_service = MagicMock()
        mock_service.check_active.return_value = True
        mock_service_class.return_value = mock_service

        context = ops.testing.Context(charm_type=Falco, charm_root=mock_charm_dir)
        state_in = ops.testing.State(
            config={"custom-config-repository": "git+ssh://github.com/user/repo.git@production"}
        )

        with context(context.on.config_changed(), state_in) as mgr:
            state = mgr.charm.state
            assert state.custom_config_repo == AnyUrl("git+ssh://github.com/user/repo.git")
            assert state.custom_config_repo_ref == "production"
            state_out = mgr.run()
            mock_service.configure.assert_called_once()
            assert state_out.unit_status == ops.testing.ActiveStatus()

    @patch("charm.FalcoService")
    def test_config_changed_without_custom_config_repository(
        self, mock_service_class, mock_charm_dir, mock_falco_layout
    ):
        """Test config_changed event without custom config repository."""
        mock_service = MagicMock()
        mock_service.check_active.return_value = True
        mock_service_class.return_value = mock_service

        context = ops.testing.Context(charm_type=Falco, charm_root=mock_charm_dir)
        state_in = ops.testing.State()

        with context(context.on.config_changed(), state_in) as mgr:
            state = mgr.charm.state
            assert state.custom_config_repo is None
            assert state.custom_config_repo_ref is None
            state_out = mgr.run()
            mock_service.configure.assert_called_once()
            assert state_out.unit_status == ops.testing.ActiveStatus()

    @patch("charm.FalcoService")
    def test_config_changed_validation_error(
        self, mock_service_class, mock_charm_dir, mock_falco_layout
    ):
        """Test config_changed with validation error."""
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        context = ops.testing.Context(charm_type=Falco, charm_root=mock_charm_dir)

        # "" is an invalid URL
        state_in = ops.testing.State(config={"custom-config-repository": ""})
        state_out = context.run(context.on.config_changed(), state_in)

        assert state_out.unit_status == ops.testing.BlockedStatus("Invalid charm config")

    @patch("charm.FalcoService")
    def test_config_changed_git_clone_error(
        self, mock_service_class, mock_charm_dir, mock_falco_layout
    ):
        """Test config_changed with git clone error."""
        mock_service = MagicMock()
        mock_service.configure.side_effect = FalcoConfigurationError("Clone failed")
        mock_service_class.return_value = mock_service

        context = ops.testing.Context(charm_type=Falco, charm_root=mock_charm_dir)
        state_in = ops.testing.State(
            config={"custom-config-repository": "git+ssh://github.com/user/repo.git"}
        )
        state_out = context.run(context.on.config_changed(), state_in)

        assert state_out.unit_status == ops.testing.BlockedStatus("Failed configuring Falco")
