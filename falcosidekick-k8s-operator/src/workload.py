# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm workload module."""

import logging
from pathlib import Path

import ops
from jinja2 import Environment, FileSystemLoader

import state

logger = logging.getLogger(__name__)

TEMPLATE_DIR = "src/templates"


class Template:
    """Template file manager.

    Manages Jinja2 template files, rendering them with context and installing
    them into containers.
    """

    def __init__(self, name: str, destination: Path, container: ops.Container) -> None:
        """Initialize the template file manager.

        Args:
            name: Template file name (relative to TEMPLATE_DIR).
            destination: Destination path for the rendered template.
            container: Container where the template will be installed.
        """
        self.name = name
        self.destination = destination
        self.container = container

        self._env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)
        self._template = self._env.get_template(self.name)

    def install(self, context: dict) -> bool:
        """Render and install template file.

        Args:
            context (dict): Context for rendering the template

        Returns:
            bool: True if there is change in configuration, False otherwise

        Raises:
            TemplateRenderError: If rendering or writing the template fails
        """
        logger.debug("Generating template file at %s", self.destination)
        try:
            old_content = self.container.pull(self.destination, encoding="utf-8").read()
        except ops.pebble.PathError:
            old_content = ""
        new_content = self._template.render(context)

        if old_content == new_content:
            logger.debug("No changes detected in rendered template at %s", self.destination)
            return False

        parent_dir = str(self.destination.parent)
        if not self.container.isdir(parent_dir):
            self.container.make_dir(parent_dir, make_parents=True)

        self.container.push(self.destination, new_content, encoding="utf-8")
        return True


class FalcosidekickConfigFile(Template):
    """Falcosidekick configuration file manager.

    Manages the Falcosidekick YAML configuration file using the template system.
    """

    template: str = "falcosidekick.yaml.j2"
    config_file: Path = Path("/etc/falcosidekick/falcosidekick.yaml")  # defined in rockcraft.yaml

    def __init__(self, container: ops.Container) -> None:
        """Initialize the Falcosidekick configuration file manager.

        Args:
            container: The container where the configuration will be installed.
        """
        super().__init__(self.template, self.config_file, container)


class Falcosidekick:
    """Falcosidekick workload class.

    See the charmcraft.yaml and rockcraft.yaml for more information about the class attributes.
    """

    command: str = "falcosidekick"  # defined in rockcraft.yaml
    sevice_name: str = "falcosidekick"  # defined in rockcraft.yaml
    container_name: str = "falcosidekick"  # defined in charmcraft.yaml

    def __init__(self, charm: ops.CharmBase) -> None:
        """Initialize the Falcosidekick workload.

        Args:
            charm: The charm instance managing this workload.
        """
        self.charm = charm
        self.config_file = FalcosidekickConfigFile(container=self.container)

    @property
    def ready(self) -> bool:
        """Determine if the Falcosidekick workload is ready for use.

        Returns:
            bool: True if the container is ready and can be connected to, False otherwise.
        """
        return self.container.can_connect()

    @property
    def health(self) -> bool:
        """Determine if the Falcosidekick workload is healthy.

        Checks all alive-level health checks for the workload.

        Returns:
            bool: True if all health checks are UP, False otherwise.
        """
        if not self.ready:
            logger.warning("Cannot determine health; container is not ready")
            return False
        checks = self.container.get_checks(level=ops.pebble.CheckLevel.ALIVE)
        return all(check.status == ops.pebble.CheckStatus.UP for check in checks.values())

    @property
    def container(self) -> ops.Container:
        """Get the Falcosidekick container.

        Returns:
            ops.Container: The Falcosidekick container instance.
        """
        return self.charm.unit.get_container(self.container_name)

    def _get_healthcheck_layer(self, port: int) -> ops.pebble.LayerDict:
        """Get the health check layer for the Falcosidekick workload.

        Args:
            port: The port on which the health check endpoint is available.

        Returns:
            ops.pebble.LayerDict: The Pebble layer configuration for health checks.
        """
        return {
            "checks": {
                "health": {
                    "level": "alive",
                    "override": "replace",
                    "http": {"url": f"http://localhost:{port}/healthz"},
                }
            }
        }

    def _configure_healthchecks(self, port: int) -> None:
        """Add healthcheck layer to the plan idempotently.

        Args:
            port: The port on which the health check endpoint is available.
        """
        healthcheck_layer = self._get_healthcheck_layer(port)
        try:
            logger.debug("Adding healthcheck layer to the plan")
            self.container.add_layer("checks", healthcheck_layer, combine=True)
        except ops.pebble.ConnectionError as connect_error:
            logger.error("Not able to add Healthcheck layer")
            logger.exception(connect_error)

    def configure(self, charm_state: state.CharmState) -> None:
        """Configure the Falcosidekick workload idempotently.

        Installs the configuration file, sets up health checks, and restarts
        services if necessary.

        Args:
            charm_state: The current charm state containing configuration parameters.
        """
        if not self.ready:
            logger.warning("Cannot configure; container is not ready")
            return

        changed = self.config_file.install(context={"charm_state": charm_state})
        if not changed:
            logger.warning("Configuration not changed; skipping reconfiguration")
            return

        self._configure_healthchecks(charm_state.falcosidekick_listenport)
        self.container.replan()

        for service_name in self.container.get_services():
            logger.debug(f"Restarting {service_name} in {self.container_name}")
            self.container.restart(service_name)
