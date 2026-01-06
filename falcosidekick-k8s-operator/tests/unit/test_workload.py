# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for workload module."""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import ops

from state import CharmState
from workload import Falcosidekick, FalcosidekickConfigFile, Template


class TestTemplate:
    """Test Template class."""

    def test_install_template_ok_with_changes(self):
        """Test template installation succeeds when configuration changes.

        Arrange: Set up mock container with old content different from new template.
        Act: Install template with new configuration.
        Assert: Template is pushed to container and returns True.
        """
        # Arrange: Set up mock container with old content
        mock_container = Mock(spec=ops.Container)
        mock_pull = Mock()
        mock_pull.read.return_value = "old content"
        mock_container.pull.return_value = mock_pull
        mock_container.isdir.return_value = True

        template = Template("falcosidekick.yaml.j2", Path("/etc/test.yaml"), mock_container)
        context = {"charm_state": Mock(falcosidekick_listenport=2801)}

        # Act: Install the template
        result = template.install(context)

        # Assert: Verify template was installed and change detected
        mock_container.push.assert_called_once()
        assert result is True
        assert mock_container.push.call_args[0][0] == Path("/etc/test.yaml")

    def test_install_template_ok_no_changes(self):
        """Test template installation when configuration hasn't changed.

        Arrange: Set up mock container with content matching new template.
        Act: Install template with same configuration.
        Assert: Template is not pushed and returns False.
        """
        # Arrange: Set up mock container with matching content
        mock_container = Mock(spec=ops.Container)

        template = Template("falcosidekick.yaml.j2", Path("/etc/test.yaml"), mock_container)
        context = {"charm_state": Mock(falcosidekick_listenport=2801)}

        # Mock the template to render specific content
        rendered_content = 'listenport: 2801\nlistenaddress: "" # ip address to bind falcosidekick to (default: "" meaning all addresses)\n'
        with patch.object(template._template, "render", return_value=rendered_content):
            mock_pull = Mock()
            mock_pull.read.return_value = rendered_content
            mock_container.pull.return_value = mock_pull

            # Act: Install the template
            result = template.install(context)

            # Assert: Verify no change detected and template not pushed
            assert result is False
            mock_container.push.assert_not_called()

    def test_install_template_creates_parent_directory(self):
        """Test template installation creates parent directory if it doesn't exist.

        Arrange: Set up mock container where parent directory doesn't exist.
        Act: Install template to path with non-existent parent directory.
        Assert: Parent directory is created and template is pushed.
        """
        # Arrange: Set up mock container where directory doesn't exist
        mock_container = Mock(spec=ops.Container)
        mock_container.pull.side_effect = ops.pebble.PathError("kind", "message")
        mock_container.isdir.return_value = False

        template = Template("falcosidekick.yaml.j2", Path("/etc/new/test.yaml"), mock_container)
        context = {"charm_state": Mock(falcosidekick_listenport=2801)}

        # Act: Install the template
        result = template.install(context)

        # Assert: Verify parent directory was created
        assert result is True
        mock_container.push.assert_called_once()
        mock_container.make_dir.assert_called_once_with("/etc/new", make_parents=True)

    def test_install_template_fail_handles_path_error(self):
        """Test template installation handles PathError when file doesn't exist.

        Arrange: Set up mock container that raises PathError on pull.
        Act: Install template when file doesn't exist.
        Assert: Template is installed treating missing file as empty content.
        """
        # Arrange: Set up mock container that raises PathError on pull
        mock_container = Mock(spec=ops.Container)
        mock_container.pull.side_effect = ops.pebble.PathError("kind", "message")
        mock_container.isdir.return_value = True

        template = Template("falcosidekick.yaml.j2", Path("/etc/test.yaml"), mock_container)
        context = {"charm_state": Mock(falcosidekick_listenport=2801)}

        # Act: Install the template
        result = template.install(context)

        # Assert: Verify template was installed (treating missing file as empty content)
        assert result is True
        mock_container.push.assert_called_once()


class TestFalcosidekick:
    """Test Falcosidekick workload class."""

    @patch("workload.Falcosidekick.health", new_callable=MagicMock)
    def test_configure_with_changes(self, mock_health):
        """Test Falcosidekick configuration when configuration changes.

        Arrange: Set up mock charm with healthy container and changed config.
        Act: Configure workload with new CharmState.
        Assert: Service is replanned and restarted.
        """
        # Arrange: Set up mock charm and container
        mock_charm = Mock(spec=ops.CharmBase)
        mock_container = Mock(spec=ops.Container)
        mock_container.can_connect.return_value = True
        mock_container.get_services.return_value = ["falcosidekick"]
        mock_charm.unit.get_container.return_value = mock_container
        mock_health.return_value = True

        # Mock the config file install to return True (changed)
        with patch.object(FalcosidekickConfigFile, "install", return_value=True):
            falcosidekick = Falcosidekick(mock_charm)
            charm_state = CharmState(
                falcosidekick_listenport=2801,
                falcosidekick_loki_endpoint="/loki/api/v1/push",
                falcosidekick_loki_hostport="http://loki:3100",
            )
            mock_http_output_provider = Mock()

            # Act: Configure the workload
            falcosidekick.configure(charm_state, mock_http_output_provider)

            # Assert: Verify replan and restart were called
            mock_container.add_layer.assert_called_once()
            mock_container.replan.assert_called_once()
            mock_container.restart.assert_called_once_with("falcosidekick")
            mock_http_output_provider.update_config.assert_called_once_with(
                path="/", scheme="http", listen_port=2801, set_ports=True
            )

    @patch("workload.Falcosidekick.health", new_callable=MagicMock)
    def test_configure_without_changes(self, mock_health):
        """Test Falcosidekick configuration when configuration hasn't changed.

        Arrange: Set up mock charm with healthy container and unchanged config.
        Act: Configure workload with same CharmState.
        Assert: Service is not replanned or restarted.
        """
        # Arrange: Set up mock charm and container
        mock_charm = Mock(spec=ops.CharmBase)
        mock_container = Mock(spec=ops.Container)
        mock_container.can_connect.return_value = True
        mock_charm.unit.get_container.return_value = mock_container
        mock_health.return_value = True

        # Mock the config file install to return False (no change)
        with patch.object(FalcosidekickConfigFile, "install", return_value=False):
            falcosidekick = Falcosidekick(mock_charm)
            charm_state = CharmState(
                falcosidekick_listenport=2801,
                falcosidekick_loki_endpoint="/loki/api/v1/push",
                falcosidekick_loki_hostport="http://loki:3100",
            )
            mock_http_output_provider = Mock()

            # Act: Configure the workload
            falcosidekick.configure(charm_state, mock_http_output_provider)

            # Assert: Verify replan and restart were NOT called
            mock_container.add_layer.assert_not_called()
            mock_container.replan.assert_not_called()
            mock_container.restart.assert_not_called()
            # But http output info should still be set
            mock_http_output_provider.update_config.assert_called_once_with(
                path="/", scheme="http", listen_port=2801, set_ports=True
            )

    def test_configure_container_not_ready(self):
        """Test Falcosidekick configuration when container is not ready.

        Arrange: Set up mock charm with container that cannot connect.
        Act: Attempt to configure workload.
        Assert: Configuration install is not called.
        """
        # Arrange: Set up mock charm with container that can't connect
        mock_charm = Mock(spec=ops.CharmBase)
        mock_container = Mock(spec=ops.Container)
        mock_container.can_connect.return_value = False
        mock_charm.unit.get_container.return_value = mock_container

        falcosidekick = Falcosidekick(mock_charm)
        charm_state = CharmState(
            falcosidekick_listenport=2801,
            falcosidekick_loki_endpoint="/loki/api/v1/push",
            falcosidekick_loki_hostport="http://loki:3100",
        )
        mock_http_output_provider = Mock()

        # Act: Attempt to configure the workload
        with patch.object(FalcosidekickConfigFile, "install") as mock_install:
            falcosidekick.configure(charm_state, mock_http_output_provider)

            # Assert: Verify install was not called
            mock_install.assert_not_called()
