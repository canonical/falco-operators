# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for Falco service module."""

import os
import subprocess
from unittest.mock import MagicMock, patch

import pytest
from pydantic import AnyUrl

import service
from service import (
    CLONE_OUTPUT_DIR,
    FALCO_CUSTOM_CONFIGS_KEY,
    FALCO_CUSTOM_RULES_KEY,
    FALCO_SERVICE_NAME,
    FalcoConfigurationError,
    FalcoCustomSetting,
    FalcoService,
    GitCloneError,
    RsyncError,
    SshKeyScanError,
    SshKeyWriteError,
    Template,
    TemplateRenderError,
)
from state import CharmState


class TestTemplate:
    """Test Template class."""

    @patch("service.Environment")
    def test_install(self, mock_env_class, tmp_path):
        """Test template installation."""
        mock_env = MagicMock()
        mock_template = MagicMock()
        mock_template.render.return_value = "rendered content"
        mock_env.get_template.return_value = mock_template
        mock_env_class.return_value = mock_env

        dest = tmp_path / "subdir" / "output.txt"
        context = {"key": "value"}
        template = Template("test.j2", dest, context)
        template.install()

        assert dest.parent.exists()
        assert dest.exists()
        assert dest.read_text() == "rendered content"
        mock_template.render.assert_called_once_with(context)

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


class TestFalcoCustomSetting:
    """Test FalcoCustomSetting class."""

    def test_install(self, mock_falco_layout, tmp_path):
        """Test FalcoCustomSetting install creates directories."""
        # Use a temporary SSH directory for testing
        test_ssh_dir = tmp_path / ".ssh"

        with patch("service.SSH_DIR", test_ssh_dir):
            custom_setting = FalcoCustomSetting(mock_falco_layout)

            # Remove directories to test creation
            mock_falco_layout.rules_dir.rmdir()
            mock_falco_layout.configs_dir.rmdir()

            custom_setting.install()

            assert mock_falco_layout.rules_dir.exists()
            assert mock_falco_layout.configs_dir.exists()
            assert test_ssh_dir.exists()

    def test_remove_deletes_yaml_files(self, mock_falco_layout):
        """Test FalcoCustomSetting remove deletes yaml files."""
        custom_setting = FalcoCustomSetting(mock_falco_layout)

        # Create some test files
        rule_file = mock_falco_layout.rules_dir / "test_rule.yaml"
        config_file = mock_falco_layout.configs_dir / "test_config.yaml"
        other_file = mock_falco_layout.rules_dir / "test.txt"

        rule_file.write_text("test rule")
        config_file.write_text("test config")
        other_file.write_text("other")

        custom_setting.remove()

        # YAML files should be deleted
        assert not rule_file.exists()
        assert not config_file.exists()
        # Non-YAML files should remain
        assert other_file.exists()

    def test_configure_no_repo(self, mock_falco_layout):
        """Test configure with no custom config repo."""
        custom_setting = FalcoCustomSetting(mock_falco_layout)

        # Create some files to verify they get removed
        rule_file = mock_falco_layout.rules_dir / "test.yaml"
        rule_file.write_text("test")

        charm_state = CharmState(custom_config_repo=None)
        custom_setting.configure(charm_state)

        # File should be removed when no repo is configured
        assert not rule_file.exists()

    @patch("service.subprocess")
    def test_configure_with_repo(self, mock_subprocess, mock_falco_layout):
        """Test configure with custom config repo."""
        custom_setting = FalcoCustomSetting(mock_falco_layout)

        # Setup mock for git commands to simulate repo already cloned
        def check_output_side_effect(cmd, *args, **kwargs):
            if "config" in cmd and "--get" in cmd:
                return b"git+ssh://git@github.com/user/repo.git\n"
            elif "describe" in cmd:
                return b"v1.0\n"
            return b""

        mock_subprocess.check_output.side_effect = check_output_side_effect

        # Create mock directories for rsync
        clone_rules_dir = CLONE_OUTPUT_DIR / FALCO_CUSTOM_RULES_KEY
        clone_configs_dir = CLONE_OUTPUT_DIR / FALCO_CUSTOM_CONFIGS_KEY
        clone_rules_dir.mkdir(parents=True, exist_ok=True)
        clone_configs_dir.mkdir(parents=True, exist_ok=True)

        # Create test files in clone directory
        (clone_rules_dir / "custom.yaml").write_text("custom rule")
        (clone_configs_dir / "custom.yaml").write_text("custom config")

        charm_state = CharmState(
            custom_config_repo=AnyUrl("git+ssh://git@github.com/user/repo.git"),
            custom_config_repo_ref="v1.0",
        )

        custom_setting.configure(charm_state)

        # Verify rsync was called
        mock_subprocess.run.assert_called()


class TestFalcoServiceEdgeCases:
    """Test edge cases for FalcoService."""

    @patch("service.systemd")
    def test_configure_with_custom_config_error(self, mock_systemd, mock_falco_layout):
        """Test FalcoService.configure handles custom config errors."""
        mock_config = MagicMock()
        mock_service_file = MagicMock()
        mock_custom_setting = MagicMock()

        falco_service = FalcoService(mock_config, mock_service_file, mock_custom_setting)

        # Mock custom_setting.configure to raise GitCloneError
        mock_custom_setting.configure.side_effect = GitCloneError("Test error")

        charm_state = CharmState(custom_config_repo=AnyUrl("https://github.com/user/repo.git"))

        with pytest.raises(FalcoConfigurationError):
            falco_service.configure(charm_state)


class TestFalcoService:
    """Test FalcoService class."""

    @patch("service.systemd")
    def test_install(self, mock_systemd):
        """Test Falco service installation."""
        mock_config = MagicMock()
        mock_service_file = MagicMock()
        mock_service_file.service_name = FALCO_SERVICE_NAME
        mock_custom_setting = MagicMock()

        service = FalcoService(mock_config, mock_service_file, mock_custom_setting)
        service.install()

        mock_config.install.assert_called_once()
        mock_service_file.install.assert_called_once()
        mock_systemd.service_enable.assert_called_once_with(FALCO_SERVICE_NAME)

    @patch("service.systemd")
    def test_remove(self, mock_systemd):
        """Test removing active Falco service."""
        mock_config = MagicMock()
        mock_service_file = MagicMock()
        mock_service_file.service_name = FALCO_SERVICE_NAME
        mock_custom_setting = MagicMock()

        service = FalcoService(mock_config, mock_service_file, mock_custom_setting)
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
        mock_service_file.context = {}
        mock_custom_setting = MagicMock()

        service = FalcoService(mock_config, mock_service_file, mock_custom_setting)
        charm_state = CharmState()
        service.configure(charm_state)

        mock_custom_setting.configure.assert_called_once_with(charm_state)
        mock_service_file.install.assert_not_called()
        mock_service_file.update.assert_called_once()
        mock_systemd.daemon_reload.assert_called_once()
        mock_systemd.service_restart.assert_called_once_with(FALCO_SERVICE_NAME)

    @patch("service.systemd")
    def test_check_active_running(self, mock_systemd):
        """Test check_active when service is running."""
        mock_systemd.service_running.return_value = True

        mock_config = MagicMock()
        mock_service_file = MagicMock()
        mock_service_file.service_name = FALCO_SERVICE_NAME
        mock_custom_setting = MagicMock()

        service = FalcoService(mock_config, mock_service_file, mock_custom_setting)
        assert service.check_active() is True
        mock_systemd.service_running.assert_called_once_with(FALCO_SERVICE_NAME)

    @patch("service.systemd")
    def test_check_active_not_running(self, mock_systemd):
        """Test check_active when service is not running."""
        mock_systemd.service_running.return_value = False

        mock_config = MagicMock()
        mock_service_file = MagicMock()
        mock_service_file.service_name = FALCO_SERVICE_NAME
        mock_custom_setting = MagicMock()

        service = FalcoService(mock_config, mock_service_file, mock_custom_setting)
        assert service.check_active() is False
        mock_systemd.service_running.assert_called_once_with(FALCO_SERVICE_NAME)


class TestUtilityFunctions:
    """Test utility functions in service module."""

    @patch("service.subprocess.run")
    def test_pull_falco_rule_files_rsync_error(self, mock_run):
        """Test _pull_falco_rule_files handles rsync error."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "rsync")

        with pytest.raises(RsyncError):
            service._pull_falco_rule_files("/dummy/destination")

    @patch("service.subprocess.run")
    def test_pull_falco_config_files_rsync_error(self, mock_run):
        """Test _pull_falco_config_files handles rsync error."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "rsync")

        with pytest.raises(RsyncError):
            service._pull_falco_config_files("/dummy/destination")

    @patch("service.subprocess")
    @patch("service.shutil")
    def test_git_clone_success(self, mock_shutil, mock_subprocess):
        """Test _git_clone with successful clone."""
        service._git_clone("git+ssh://git@github.com/user/repo.git", ref="main")

        mock_shutil.rmtree.assert_called_once()
        mock_subprocess.run.assert_called_once()

        # Verify git clone command
        call_args = mock_subprocess.run.call_args[0][0]
        assert "clone" in call_args
        assert "--depth" in call_args
        assert "1" in call_args
        assert "-b" in call_args
        assert "main" in call_args

    @patch("service.subprocess.run")
    @patch("service.shutil")
    def test_git_clone_error(self, mock_shutil, mock_run):
        """Test _git_clone handles clone error."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        with pytest.raises(GitCloneError):
            service._git_clone("git+ssh://git@github.com/user/repo.git")

    @patch("service.subprocess")
    def test_setup_ssh_key_success(self, mock_subprocess, tmp_path):
        """Test _setup_ssh_key writes key correctly."""
        # Use a temporary file for testing
        test_ssh_key_file = tmp_path / "id_rsa"

        with patch("service.SSH_KEY_FILE", test_ssh_key_file):
            ssh_key = "-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----"
            service._setup_ssh_key(ssh_key)

            assert test_ssh_key_file.exists()
            assert test_ssh_key_file.read_text() == ssh_key
            # Check permissions (0o600)
            assert oct(os.stat(test_ssh_key_file).st_mode)[-3:] == "600"

    def test_setup_ssh_key_write_error(self, tmp_path):
        """Test _setup_ssh_key handles write error."""
        # Use a read-only directory
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o444)
        test_ssh_key_file = readonly_dir / "id_rsa"

        with patch("service.SSH_KEY_FILE", test_ssh_key_file), pytest.raises(SshKeyWriteError):
            service._setup_ssh_key("test key")

        # Cleanup
        readonly_dir.chmod(0o755)

    @patch("service.subprocess")
    def test_add_known_hosts_success(self, mock_subprocess, tmp_path):
        """Test _add_known_hosts adds host key."""
        test_known_hosts = tmp_path / "known_hosts"

        mock_subprocess.check_output.return_value = b"github.com ssh-rsa AAAA..."

        with patch("service.KNOWN_HOSTS_FILE", test_known_hosts):
            service._add_known_hosts("github.com")

            assert test_known_hosts.exists()
            assert "github.com ssh-rsa AAAA..." in test_known_hosts.read_text()

    @patch("service.subprocess.check_output")
    def test_add_known_hosts_keyscan_error(self, mock_check_output):
        """Test _add_known_hosts handles keyscan error."""
        mock_check_output.side_effect = subprocess.CalledProcessError(1, "ssh-keyscan")

        with pytest.raises(SshKeyScanError):
            service._add_known_hosts("github.com")

    @patch("service.subprocess.check_output")
    def test_add_known_hosts_write_error(self, mock_check_output, tmp_path):
        """Test _add_known_hosts handles write error."""
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o444)
        test_known_hosts = readonly_dir / "known_hosts"

        mock_check_output.return_value = b"host key"

        with patch("service.KNOWN_HOSTS_FILE", test_known_hosts), pytest.raises(SshKeyScanError):
            # OSError is caught and re-raised as SshKeyScanError
            service._add_known_hosts("github.com")

        # Cleanup
        readonly_dir.chmod(0o755)

    @patch("service.subprocess")
    def test_get_cloned_repo_url_success(self, mock_subprocess):
        """Test _get_cloned_repo_url returns URL."""
        mock_subprocess.check_output.return_value = b"git+ssh://git@github.com/user/repo.git\n"

        url = service._get_cloned_repo_url()
        assert url == "git+ssh://git@github.com/user/repo.git"

    @patch("service.subprocess.check_output")
    def test_get_cloned_repo_url_not_cloned(self, mock_check_output):
        """Test _get_cloned_repo_url when repo not cloned."""
        mock_check_output.side_effect = subprocess.CalledProcessError(1, "git")

        url = service._get_cloned_repo_url()
        assert url == ""

    @patch("service.subprocess")
    def test_get_cloned_repo_tag_success(self, mock_subprocess):
        """Test _get_cloned_repo_tag returns tag."""
        mock_subprocess.check_output.return_value = b"v1.0.0\n"

        tag = service._get_cloned_repo_tag()
        assert tag == "v1.0.0"

    @patch("service.subprocess.check_output")
    def test_get_cloned_repo_tag_no_tag(self, mock_check_output):
        """Test _get_cloned_repo_tag when no tag exists."""
        mock_check_output.side_effect = subprocess.CalledProcessError(1, "git")

        tag = service._get_cloned_repo_tag()
        assert tag == ""

    @patch("service.subprocess")
    def test_git_sync_already_synced(self, mock_subprocess):
        """Test _git_sync returns early if repo already synced."""

        # Mock that repo is already cloned with same URL and tag
        def check_output_side_effect(cmd, *args, **kwargs):
            if "config" in cmd:
                return b"git+ssh://git@github.com/user/repo.git\n"
            elif "describe" in cmd:
                return b"v1.0\n"
            return b""

        mock_subprocess.check_output.side_effect = check_output_side_effect

        service._git_sync("git+ssh://git@github.com/user/repo.git", "github.com", ref="v1.0")

        # Should not call run (git clone) if already synced
        mock_subprocess.run.assert_not_called()

    @patch("service.subprocess.check_output")
    @patch("service.subprocess.run")
    def test_git_sync_with_ssh_key(self, mock_run, mock_check_output, tmp_path):
        """Test _git_sync sets up SSH key when provided."""
        test_ssh_key_file = tmp_path / "id_rsa"
        test_known_hosts = tmp_path / "known_hosts"

        with (
            patch("service.SSH_KEY_FILE", test_ssh_key_file),
            patch("service.KNOWN_HOSTS_FILE", test_known_hosts),
        ):
            # Mock check_output calls: repo URL check, tag check, and keyscan
            # _git_sync calls _get_cloned_repo_url, _get_cloned_repo_tag, and _add_known_hosts
            mock_check_output.side_effect = [
                subprocess.CalledProcessError(1, "git"),  # get_cloned_repo_url
                subprocess.CalledProcessError(1, "git"),  # get_cloned_repo_tag
                b"github.com ssh-rsa AAAA...\n",  # add_known_hosts
            ]

            service._git_sync(
                "git+ssh://git@github.com/user/repo.git", "github.com", ssh_private_key="test-key"
            )

            # Verify SSH key was written
            assert test_ssh_key_file.exists()
            assert test_ssh_key_file.read_text() == "test-key"

    @patch("service.subprocess.check_output")
    @patch("service.subprocess.run")
    def test_git_sync_without_ssh_key(self, mock_run, mock_check_output, tmp_path):
        """Test _git_sync without SSH key (e.g., public repo)."""
        test_known_hosts = tmp_path / "known_hosts"

        with patch("service.KNOWN_HOSTS_FILE", test_known_hosts):
            # Mock check_output calls
            mock_check_output.side_effect = [
                subprocess.CalledProcessError(1, "git"),  # get_cloned_repo_url
                subprocess.CalledProcessError(1, "git"),  # get_cloned_repo_tag
                b"github.com ssh-rsa AAAA...\n",  # add_known_hosts
            ]

            # Call without ssh_private_key parameter
            service._git_sync("https://github.com/user/repo.git", "github.com")

            # Verify git clone was called
            mock_run.assert_called_once()
