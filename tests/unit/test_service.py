# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for Falco service module."""

from unittest.mock import MagicMock, patch

import pytest

from service import (
    FALCO_SERVICE_NAME,
    FalcoConfig,
    FalcoLayout,
    FalcoService,
    FalcoServiceFile,
    Template,
    TemplateRenderError,
)


class TestFalcoLayout:
    """Test FalcoLayout class."""

    def test_init_valid_directory(self, falco_base_dir):
        """Test initialization with valid directory."""
        layout = FalcoLayout(falco_base_dir)

        assert layout.home == falco_base_dir
        assert layout.cmd == falco_base_dir / "usr/bin/falco"
        assert layout.plugins_dir == falco_base_dir / "usr/share/falco/plugins"
        assert layout.default_rules_dir == falco_base_dir / "etc/falco/default_rules"
        assert layout.rules_dir == falco_base_dir / "etc/falco/rules.d"
        assert layout.config_file == falco_base_dir / "etc/falco/falco.yaml"

    def test_init_creates_rules_dir(self, falco_base_dir):
        """Test that initialization creates rules directory."""
        layout = FalcoLayout(falco_base_dir)
        assert layout.rules_dir.exists()
        assert layout.rules_dir.is_dir()

    def test_init_nonexistent_directory(self, tmp_path):
        """Test initialization with nonexistent directory."""
        nonexistent = tmp_path / "nonexistent"
        with pytest.raises(ValueError, match="does not exist or is not a directory"):
            FalcoLayout(nonexistent)

    def test_init_file_not_directory(self, tmp_path):
        """Test initialization with a file instead of directory."""
        file_path = tmp_path / "file"
        file_path.touch()
        with pytest.raises(ValueError, match="does not exist or is not a directory"):
            FalcoLayout(file_path)


class TestTemplate:
    """Test Template class."""

    @patch("service.Environment")
    def test_init(self, mock_env_class, tmp_path):
        """Test template initialization."""
        mock_env = MagicMock()
        mock_template = MagicMock()
        mock_env.get_template.return_value = mock_template
        mock_env_class.return_value = mock_env

        dest = tmp_path / "output.txt"
        context = {"key": "value"}
        template = Template("test.j2", dest, context)

        assert template.name == "test.j2"
        assert template.destination == dest
        assert template.context == context
        mock_env.get_template.assert_called_once_with("test.j2")

    @patch("service.Environment")
    def test_init_empty_context(self, mock_env_class, tmp_path):
        """Test template initialization with None context."""
        mock_env = MagicMock()
        mock_env_class.return_value = mock_env

        template = Template("test.j2", tmp_path / "output.txt", None)
        assert template.context == {}

    @patch("service.Environment")
    def test_install(self, mock_env_class, tmp_path):
        """Test template installation."""
        mock_env = MagicMock()
        mock_template = MagicMock()
        mock_template.render.return_value = "rendered content"
        mock_env.get_template.return_value = mock_template
        mock_env_class.return_value = mock_env

        dest = tmp_path / "output.txt"
        context = {"key": "value"}
        template = Template("test.j2", dest, context)
        template.install()

        assert dest.exists()
        assert dest.read_text() == "rendered content"
        mock_template.render.assert_called_once_with(context)

    @patch("service.Environment")
    def test_install_creates_parent_directory(self, mock_env_class, tmp_path):
        """Test that install creates parent directories."""
        mock_env = MagicMock()
        mock_template = MagicMock()
        mock_template.render.return_value = "content"
        mock_env.get_template.return_value = mock_template
        mock_env_class.return_value = mock_env

        dest = tmp_path / "subdir" / "output.txt"
        template = Template("test.j2", dest, {})
        template.install()

        assert dest.parent.exists()
        assert dest.exists()

    @patch("service.Environment")
    def test_remove(self, mock_env_class, tmp_path):
        """Test template removal."""
        mock_env = MagicMock()
        mock_env_class.return_value = mock_env

        dest = tmp_path / "output.txt"
        dest.touch()

        template = Template("test.j2", dest, {})
        template.remove()

        assert not dest.exists()

    @patch("service.Environment")
    def test_remove_nonexistent(self, mock_env_class, tmp_path):
        """Test removing nonexistent template file."""
        mock_env = MagicMock()
        mock_env_class.return_value = mock_env

        dest = tmp_path / "nonexistent.txt"
        template = Template("test.j2", dest, {})
        template.remove()

    @patch("service.Environment")
    def test_render_write_error(self, mock_env_class, tmp_path):
        """Test render error handling."""
        mock_env = MagicMock()
        mock_template = MagicMock()
        mock_template.render.return_value = "content"
        mock_env.get_template.return_value = mock_template
        mock_env_class.return_value = mock_env

        # Use a path that will cause write error
        dest = tmp_path / "readonly" / "output.txt"
        dest.parent.mkdir()
        dest.parent.chmod(0o444)

        template = Template("test.j2", dest, {})

        with pytest.raises(TemplateRenderError, match="Failed to write template"):
            template.install()


class TestFalcoServiceFile:
    """Test FalcoServiceFile class."""

    @patch("service.Environment")
    def test_init(self, mock_env_class, falco_base_dir):
        """Test FalcoServiceFile initialization."""
        mock_env = MagicMock()
        mock_env_class.return_value = mock_env

        layout = FalcoLayout(falco_base_dir)
        service_file = FalcoServiceFile(layout)

        assert service_file.service_name == FALCO_SERVICE_NAME
        assert "falco.service.j2" in service_file.name
        assert service_file.context["command"] == str(layout.cmd)
        assert service_file.context["rules_dir"] == str(layout.rules_dir)
        assert service_file.context["config_file"] == str(layout.config_file)


class TestFalcoConfig:
    """Test FalcoConfig class."""

    @patch("service.Environment")
    @patch("service.JujuTopology")
    def test_init(self, mock_topology_class, mock_env_class, falco_base_dir, mock_charm):
        """Test FalcoConfig initialization."""
        mock_env = MagicMock()
        mock_env_class.return_value = mock_env

        mock_topology = MagicMock()
        mock_topology.as_dict.return_value = {"model": "test-model"}
        mock_topology_class.from_charm.return_value = mock_topology

        layout = FalcoLayout(falco_base_dir)
        config = FalcoConfig(layout, mock_charm)

        assert "falco.yaml.j2" in config.name
        assert config.destination == layout.config_file
        assert config.context["falco_home"] == str(layout.home)
        assert config.context["juju_topology"] == {"model": "test-model"}
        mock_topology_class.from_charm.assert_called_once_with(mock_charm)


class TestFalcoService:
    """Test FalcoService class."""

    @patch("service.systemd")
    def test_install(self, mock_systemd):
        """Test Falco service installation."""
        mock_config = MagicMock()
        mock_service_file = MagicMock()
        mock_service_file.service_name = FALCO_SERVICE_NAME

        service = FalcoService(mock_config, mock_service_file)
        service.install()

        mock_config.install.assert_called_once()
        mock_service_file.install.assert_called_once()
        mock_systemd.service_enable.assert_called_once_with(FALCO_SERVICE_NAME)

    @patch("service.systemd")
    def test_remove_service(self, mock_systemd):
        """Test removing active Falco service."""
        mock_config = MagicMock()
        mock_service_file = MagicMock()
        mock_service_file.service_name = FALCO_SERVICE_NAME

        service = FalcoService(mock_config, mock_service_file)
        service.remove()

        mock_systemd.service_stop.assert_called_once_with(FALCO_SERVICE_NAME)
        mock_systemd.service_disable.assert_called_once_with(FALCO_SERVICE_NAME)
        mock_systemd.daemon_reload.assert_called_once()
        mock_config.remove.assert_called_once()
        mock_service_file.remove.assert_called_once()

    @patch("service.systemd")
    def test_configure(self, mock_systemd):
        """Test Falco service configuration."""
        mock_config = MagicMock()
        mock_service_file = MagicMock()
        mock_service_file.service_name = FALCO_SERVICE_NAME

        service = FalcoService(mock_config, mock_service_file)
        service.configure()

        mock_systemd.daemon_reload.assert_called_once()
        mock_systemd.service_restart.assert_called_once_with(FALCO_SERVICE_NAME)

    @patch("service.systemd")
    def test_check_active_running(self, mock_systemd):
        """Test check_active when service is running."""
        mock_systemd.service_running.return_value = True

        mock_config = MagicMock()
        mock_service_file = MagicMock()
        mock_service_file.service_name = FALCO_SERVICE_NAME

        service = FalcoService(mock_config, mock_service_file)
        assert service.check_active() is True
        mock_systemd.service_running.assert_called_once_with(FALCO_SERVICE_NAME)

    @patch("service.systemd")
    def test_check_active_not_running(self, mock_systemd):
        """Test check_active when service is not running."""
        mock_systemd.service_running.return_value = False

        mock_config = MagicMock()
        mock_service_file = MagicMock()
        mock_service_file.service_name = FALCO_SERVICE_NAME

        service = FalcoService(mock_config, mock_service_file)
        assert service.check_active() is False
        mock_systemd.service_running.assert_called_once_with(FALCO_SERVICE_NAME)
