# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Falco workload management module."""

import logging
from pathlib import Path
from typing import Optional

from charmlibs import systemd
from cosl import JujuTopology
from jinja2 import Environment, FileSystemLoader
from ops.charm import CharmBase

logger = logging.getLogger(__name__)


FALCO_SERVICE_NAME = "falco"

TEMPLATE_DIR = "src/templates"
SYSTEMD_SERVICE_DIR = Path("/etc/systemd/system")


class TemplateRenderError(Exception):
    """Exception raised when template rendering fails."""


class FalcoLayout:
    """Falco file layout.

    These are constant paths defined in the `charmcraft.yaml`, and they are created when the charm
    packs. Also see `.github/workflows/build_falco.yaml`.
    """

    cmd: Path = Path("usr/bin/falco")
    plugins_dir: Path = Path("usr/share/falco/plugins")
    default_rules_dir: Path = Path("etc/falco/default_rules")

    def __init__(self, base_dir: Path) -> None:
        """Initialize Falco file layout.

        Args:
            base_dir (Path): Base directory where Falco files are located
        """
        self.home = base_dir
        if not self.home.exists() or not self.home.is_dir():
            raise ValueError(f"Base directory {self.home} does not exist or is not a directory")

        self.cmd = self.home / self.cmd
        self.plugins_dir = self.home / self.plugins_dir
        self.default_rules_dir = self.home / self.default_rules_dir

        self.rules_dir = self.home / "etc/falco/rules.d"
        self.config_file = self.home / "etc/falco/falco.yaml"

        self.rules_dir.mkdir(parents=True, exist_ok=True)


class Template:
    """Template file manager."""

    def __init__(self, name: str, destination: Path, context: Optional[dict]) -> None:
        """Initialize the template file manager.

        Args:
            name (str): Template file name
            destination (Path): Destination path for the rendered template
            context (Optional[dict]): Context for rendering the template
        """
        self.name = name
        self.destination = destination
        self.context = context or {}

        self._env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)
        self._template = self._env.get_template(self.name)

    def install(self) -> None:
        """Install template file."""
        self._render(self.context)

    def remove(self) -> None:
        """Remove template file."""
        if self.destination.exists():
            self.destination.unlink()

    def _render(self, context: dict) -> None:
        """Render template file from a template.

        Args:
            context (dict): Context for rendering the template

        Raises:
            TemplateRenderError: If rendering or writing the template fails
        """
        try:
            logger.debug("Generating template file at %s", self.destination)
            content = self._template.render(context)
            if not self.destination.parent.exists():
                self.destination.parent.mkdir(parents=True, exist_ok=True)
            self.destination.write_text(content, encoding="utf-8")
            logger.debug("Template file generated at %s", self.destination)
        except OSError as e:
            logger.exception("Failed to write template to %s", self.destination)
            raise TemplateRenderError(f"Failed to write template to {self.destination}") from e


class FalcoServiceFile(Template):
    """Falco service file manager."""

    service_name = FALCO_SERVICE_NAME
    template: str = "falco.service.j2"
    service_file: Path = SYSTEMD_SERVICE_DIR / f"{FALCO_SERVICE_NAME}.service"

    def __init__(self, falco_layout: FalcoLayout) -> None:
        """Initialize the Falco service file manager."""
        super().__init__(
            self.template,
            self.service_file,
            context={
                "command": str(falco_layout.cmd),
                "rules_dir": str(falco_layout.rules_dir),
                "config_file": str(falco_layout.config_file),
            },
        )


class FalcoConfig(Template):
    """Falco config file manager."""

    template: str = "falco.yaml.j2"

    def __init__(self, falco_layout: FalcoLayout, charm: CharmBase) -> None:
        """Initialize the Falco config file manager."""
        super().__init__(
            self.template,
            falco_layout.config_file,
            context={
                "falco_home": str(falco_layout.home),
                "juju_topology": JujuTopology.from_charm(charm).as_dict(),
            },
        )


class FalcoService:
    """Falco service manager."""

    def __init__(self, config_file: FalcoConfig, service_file: FalcoServiceFile) -> None:
        self.config_file = config_file
        self.service_file = service_file

    def install(self) -> None:
        """Install and configure the Falco service."""
        logger.info("Installing Falco service")

        self.config_file.install()
        self.service_file.install()
        self.configure()

        systemd.service_enable(self.service_file.service_name)

        logger.info("Falco service installed")

    def remove(self) -> None:
        """Remove the Falco service and clean up files."""
        logger.info("Removing Falco service")

        systemd.service_stop(self.service_file.service_name)
        systemd.service_disable(self.service_file.service_name)
        systemd.daemon_reload()

        self.config_file.remove()
        self.service_file.remove()

        logger.info("Falco service removed")

    def configure(self) -> None:
        """Configure the Falco service."""
        logger.info("Configuring Falco service")

        systemd.daemon_reload()
        systemd.service_restart(self.service_file.service_name)

        logger.info("Falco service configured and started")

    def check_active(self) -> bool:
        """Check if the Falco service is active."""
        return systemd.service_running(self.service_file.service_name)
