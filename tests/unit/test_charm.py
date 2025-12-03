# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for Falco charm."""

from unittest.mock import MagicMock, patch

import ops
import ops.testing
import pytest
from scenario.errors import UncaughtCharmError

from charm import Charm


class TestCharm:
    """Test Charm class."""

    @patch("charm.FalcoService")
    def test_charm_initialization(self, mock_service, mock_charm_dir):
        """Test charm initialization."""
        context = ops.testing.Context(charm_type=Charm, charm_root=mock_charm_dir)
        state = ops.testing.State()

        with context(context.on.install(), state) as manager:
            charm = manager.charm
            assert charm.falco_layout is not None
            assert charm.falco_service_file is not None
            assert charm.managed_falco_config is not None
            assert charm.falco_service is not None

    def test_charm_initialization_missing_falco_directory(self, mock_charm_dir):
        """Test charm initialization when Falco directory is missing."""
        import shutil

        context = ops.testing.Context(charm_type=Charm, charm_root=mock_charm_dir)
        state = ops.testing.State()

        # Remove the falco directory that was created by the fixture
        shutil.rmtree(mock_charm_dir / "falco")

        with pytest.raises(UncaughtCharmError, match=r"ValueError.*does not exist"):
            context.run(context.on.install(), state)

    @patch("charm.FalcoService")
    def test_on_install(self, mock_service_class, mock_charm_dir):
        """Test the install event handler."""
        mock_service = MagicMock()
        mock_service.check_active.return_value = True
        mock_service_class.return_value = mock_service

        context = ops.testing.Context(charm_type=Charm, charm_root=mock_charm_dir)
        state_in = ops.testing.State()
        state_out = context.run(context.on.install(), state_in)

        mock_service.install.assert_called_once()
        mock_service.check_active.assert_called()
        assert state_out.unit_status == ops.testing.ActiveStatus()

    @patch("charm.FalcoService")
    def test_on_install_service_not_active_after_install(self, mock_service_class, mock_charm_dir):
        """Test install event when service is not active after installation."""
        mock_service = MagicMock()
        mock_service.check_active.return_value = False
        mock_service_class.return_value = mock_service

        context = ops.testing.Context(charm_type=Charm, charm_root=mock_charm_dir)
        state_in = ops.testing.State()

        with pytest.raises(RuntimeError, match=r"Falco service is not running"):
            context.run(context.on.install(), state_in)

        mock_service.install.assert_called_once()
        mock_service.check_active.assert_called_once()

    @patch("charm.FalcoService")
    def test_on_upgrade_charm(self, mock_service_class, mock_charm_dir):
        """Test the upgrade_charm event handler."""
        mock_service = MagicMock()
        mock_service.check_active.return_value = True
        mock_service_class.return_value = mock_service

        context = ops.testing.Context(charm_type=Charm, charm_root=mock_charm_dir)
        state_in = ops.testing.State()
        state_out = context.run(context.on.upgrade_charm(), state_in)

        mock_service.install.assert_called_once()
        mock_service.check_active.assert_called()
        assert state_out.unit_status == ops.testing.ActiveStatus()

    @patch("charm.FalcoService")
    def test_on_upgrade_fails_service_exception(self, mock_service_class, mock_charm_dir):
        """Test upgrade_charm event when service installation raises an exception."""
        mock_service = MagicMock()
        mock_service.install.side_effect = OSError("Upgrade failed")
        mock_service_class.return_value = mock_service

        context = ops.testing.Context(charm_type=Charm, charm_root=mock_charm_dir)
        state_in = ops.testing.State()

        with pytest.raises(UncaughtCharmError, match=r"OSError.*Upgrade failed"):
            context.run(context.on.upgrade_charm(), state_in)

        mock_service.install.assert_called_once()

    @patch("charm.FalcoService")
    def test_on_upgrade_service_not_active_after_upgrade(self, mock_service_class, mock_charm_dir):
        """Test upgrade_charm event when service is not active after upgrade."""
        mock_service = MagicMock()
        mock_service.check_active.return_value = False
        mock_service_class.return_value = mock_service

        context = ops.testing.Context(charm_type=Charm, charm_root=mock_charm_dir)
        state_in = ops.testing.State()

        with pytest.raises(RuntimeError, match=r"Falco service is not running"):
            context.run(context.on.upgrade_charm(), state_in)

        mock_service.install.assert_called_once()
        mock_service.check_active.assert_called_once()

    @patch("charm.FalcoService")
    def test_on_remove(self, mock_service_class, mock_charm_dir):
        """Test the remove event handler."""
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        context = ops.testing.Context(charm_type=Charm, charm_root=mock_charm_dir)
        state_in = ops.testing.State()
        state_out = context.run(context.on.remove(), state_in)

        mock_service.remove.assert_called_once()
        assert state_out.unit_status == ops.testing.MaintenanceStatus("Removing Falco service")

    @patch("charm.FalcoService")
    def test_on_remove_fails_service_exception(self, mock_service_class, mock_charm_dir):
        """Test remove event when service removal raises an exception."""
        mock_service = MagicMock()
        mock_service.remove.side_effect = PermissionError("Cannot remove service")
        mock_service_class.return_value = mock_service

        context = ops.testing.Context(charm_type=Charm, charm_root=mock_charm_dir)
        state_in = ops.testing.State()

        with pytest.raises(UncaughtCharmError, match=r"PermissionError.*Cannot remove service"):
            context.run(context.on.remove(), state_in)

        mock_service.remove.assert_called_once()

    @patch("charm.FalcoService")
    def test_update_status_active(self, mock_service_class, mock_charm_dir):
        """Test update_status when Falco service is running."""
        mock_service = MagicMock()
        mock_service.check_active.return_value = True
        mock_service_class.return_value = mock_service

        context = ops.testing.Context(charm_type=Charm, charm_root=mock_charm_dir)
        state_in = ops.testing.State()
        state_out = context.run(context.on.update_status(), state_in)

        mock_service.check_active.assert_called_once()
        assert state_out.unit_status == ops.testing.ActiveStatus()

    @patch("charm.FalcoService")
    def test_update_status_inactive(self, mock_service_class, mock_charm_dir):
        """Test update_status when Falco service is not running."""
        mock_service = MagicMock()
        mock_service.check_active.return_value = False
        mock_service_class.return_value = mock_service

        context = ops.testing.Context(charm_type=Charm, charm_root=mock_charm_dir)
        state_in = ops.testing.State()

        with pytest.raises(
            UncaughtCharmError, match=r"RuntimeError.*Falco service is not running"
        ):
            context.run(context.on.update_status(), state_in)
