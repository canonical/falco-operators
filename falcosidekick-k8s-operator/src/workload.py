# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm workload module."""

import logging
from pathlib import Path

import ops
from charms.traefik_k8s.v2.ingress import IngressPerAppRequirer
from jinja2 import Environment, FileSystemLoader
from pfe.interfaces.falcosidekick_http_endpoint import HttpEndpointProvider

import state
from certificates import TlsCertificateRequirer

logger = logging.getLogger(__name__)

TEMPLATE_DIR = "src/templates"
TLS_HEALTH_CHECK_PORT = 2810  # Falcosidekick TLS healthcheck port (hardcoded)


class MissingLokiRelationError(Exception):
    """Exception raised when the Loki relation is missing."""


class RequireOneOfIngressOrCertificateRelationError(Exception):
    """Exception raised when the not one of ingress or certificate relation exists."""


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
            True if there is change in configuration and the template is installed. Otherwise,
            False if no changes detected and the template is not installed.
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

        logger.debug("Installing template file at %s", self.destination)
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
            True if the container is ready and can be connected to, False otherwise.
        """
        return self.container.can_connect()

    @property
    def container(self) -> ops.Container:
        """Get the Falcosidekick container.

        Returns:
            The Falcosidekick container instance.
        """
        return self.charm.unit.get_container(self.container_name)

    def _get_healthcheck_layer(self, port: int) -> ops.pebble.LayerDict:
        """Get the health check layer for the Falcosidekick workload.

        Args:
            port: The port on which the health check endpoint is available.

        Returns:
            The Pebble layer configuration for health checks.
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

    def _stop_all(self) -> None:
        """Stop all services and health checks in the container."""
        for name, check in self.container.get_checks().items():
            if check.status != ops.pebble.CheckStatus.INACTIVE:
                self.container.stop_checks(name)
            logger.debug("Stopped check: %s in %s", name, self.container_name)
        for name, svc in self.container.get_services().items():
            if svc.is_running():
                self.container.stop(name)
            logger.debug("Stopped service: %s in %s", name, self.container_name)

    def configure(
        self,
        charm_state: state.CharmState,
        http_endpoint_provider: HttpEndpointProvider,
        tls_certificate_requirer: TlsCertificateRequirer,
        ingress_requirer: IngressPerAppRequirer,
    ) -> None:
        """Configure the Falcosidekick workload idempotently.

        Installs the configuration file, sets up health checks, and restarts
        services if necessary.

        Args:
            charm_state: The current charm state containing configuration parameters.
            http_endpoint_provider: The HttpEndpointManager instance to set http output data.
            tls_certificate_requirer: The TlsCertificateRequirer instance to manage TLS certificates.
            ingress_requirer: The IngressPerAppRequirer instance to manage ingress relation.

        Raises:
            MissingLokiRelationError: If the Loki relation is missing.
            RequireOneOfIngressOrCertificateRelationError: If not one of ingress or certificate relation exists.
        """
        if not self.ready:
            logger.warning("Cannot configure; container is not ready")
            return

        if not charm_state.falcosidekick_loki_hostport:
            self._stop_all()
            raise MissingLokiRelationError(
                "send-loki-logs relation is missing; Falcosidekick requires at least one output"
            )

        if not (tls_certificate_requirer.is_created() ^ ingress_requirer.is_ready()):
            self._stop_all()
            raise RequireOneOfIngressOrCertificateRelationError(
                "only one of [certificates|ingress] relation is required but not both or none"
            )

        # Set http output information idempotently
        http_endpoint_provider.update_config(**charm_state.http_endpoint_config)

        # Configure ingress idempotently
        ingress_requirer.provide_ingress_requirements(
            scheme="https",
            host=self.charm.model.app.name,
            port=charm_state.falcosidekick_listenport,
        )

        # Configure tls certificate idempotently
        cert_changed = tls_certificate_requirer.configure(container=self.container)

        # Install configuration file
        changed = self.config_file.install(context={"charm_state": charm_state})
        if not changed and not cert_changed:
            logger.warning("Configuration or certificate not changed; skipping reconfiguration")
            return

        self._configure_healthchecks(
            TLS_HEALTH_CHECK_PORT
            if charm_state.enable_tls
            else charm_state.falcosidekick_listenport
        )
        self.container.replan()

        for service_name in self.container.get_services():
            logger.debug(f"Restarting {service_name} in {self.container_name}")
            self.container.restart(service_name)
