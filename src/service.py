# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Falco workload management module."""

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from charmlibs import systemd
from cosl import JujuTopology
from jinja2 import Environment, FileSystemLoader
from ops.charm import CharmBase

import state

logger = logging.getLogger(__name__)

# Executable paths
GIT = "/usr/bin/git"
RSYNC = "/usr/bin/rsync"
SSH_KEYSCAN = "/usr/bin/ssh-keyscan"

# Ssh related paths
SSH_DIR = Path.home() / ".ssh"
SSH_KEY_FILE = SSH_DIR / "id_rsa"
KNOWN_HOSTS_FILE = SSH_DIR / "known_hosts"

# Keys to look for in the falco custom config repo.
# See `custom-config-repo` config option in `charmcraft.yaml` to learn more.
FALCO_CUSTOM_RULES_KEY = "rules.d"
FALCO_CUSTOM_CONFIGS_KEY = "config.override.d"

# Clone output directory
CLONE_OUTPUT_DIR = Path.home() / "custom-falco-config-repository"


FALCO_SERVICE_NAME = "falco"

TEMPLATE_DIR = "src/templates"
SYSTEMD_SERVICE_DIR = Path("/etc/systemd/system")


class RsyncError(Exception):
    """Exception raised when rsync fails."""


class GitCloneError(Exception):
    """Exception raised when git clone fails."""


class SshKeyScanError(Exception):
    """Exception raised when Ssh keyscan fails."""


class SshKeyWriteError(Exception):
    """Exception raised when writing Ssh key fails."""


class TemplateRenderError(Exception):
    """Exception raised when template rendering fails."""


class FalcoConfigurationError(Exception):
    """Exception raised when Falco configuration fails."""


class FalcoLayout:
    """Falco file layout.

    These are constant paths defined in the `charmcraft.yaml`, and they are created when the charm
    packs. Also see `.github/workflows/build_falco.yaml`.
    """

    _cmd: Path = Path("usr/bin/falco")
    _plugins_dir: Path = Path("usr/share/falco/plugins")
    _default_rules_dir: Path = Path("etc/falco/default_rules")

    def __init__(self, base_dir: Path) -> None:
        """Initialize Falco file layout.

        Args:
            base_dir (Path): Base directory where Falco files are located
        """
        self.home = base_dir
        if not self.home.exists() or not self.home.is_dir():
            raise ValueError(f"Base directory {self.home} does not exist or is not a directory")
        self.rules_dir.mkdir(parents=True, exist_ok=True)
        self.configs_dir.mkdir(parents=True, exist_ok=True)

    @property
    def cmd(self) -> Path:
        """Get the full path to the Falco command."""
        return self.home / self._cmd

    @property
    def plugins_dir(self) -> Path:
        """Get the full path to the Falco plugins directory."""
        return self.home / self._plugins_dir

    @property
    def default_rules_dir(self) -> Path:
        """Get the full path to the Falco default rules directory."""
        return self.home / self._default_rules_dir

    @property
    def rules_dir(self) -> Path:
        """Get the full path to the Falco rules directory."""
        return self.home / "etc/falco/rules.d"

    @property
    def configs_dir(self) -> Path:
        """Get the full path to the Falco configuration directory."""
        return self.home / "etc/falco/config.overrides.d"

    @property
    def config_file(self) -> Path:
        """Get the full path to the Falco configuration file."""
        return self.home / "etc/falco/falco.yaml"


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

    def __init__(self, falco_layout: FalcoLayout, charm: CharmBase) -> None:
        """Initialize the Falco service file manager."""
        super().__init__(
            self.template,
            self.service_file,
            context={
                "command": str(falco_layout.cmd),
                "rules_dir": str(falco_layout.rules_dir),
                "config_file": str(falco_layout.config_file),
                "falco_home": str(falco_layout.home),
                "juju_topology": JujuTopology.from_charm(charm).as_dict(),
            },
        )


class FalcoConfigFile(Template):
    """Falco config file manager."""

    template: str = "falco.yaml.j2"

    def __init__(self, falco_layout: FalcoLayout) -> None:
        """Initialize the Falco config file manager."""
        super().__init__(
            self.template,
            falco_layout.config_file,
            context={
                "falco_home": str(falco_layout.home),
            },
        )


class FalcoCustomSetting:
    """Falco custom setting manager.

    Falco custom setting means the custom falco configuration files and custom falco rules files.
    """

    def __init__(self, falco_layout: FalcoLayout) -> None:
        """Initialize the Falco custom setting manager.

        Args:
            falco_layout (FalcoLayout): The Falco file layout
        """
        self.falco_layout = falco_layout

    def install(self) -> None:
        """Install the Falco custom settings."""
        logger.info("Installing Falco custom settings")

        # Ensure the custom rules and config directories exist
        self.falco_layout.rules_dir.mkdir(parents=True, exist_ok=True)
        self.falco_layout.configs_dir.mkdir(parents=True, exist_ok=True)

        # Ensure SSH directory exists
        SSH_DIR.mkdir(mode=0o700, exist_ok=True)

        logger.info("Falco custom settings installed")

    def remove(self) -> None:
        """Remove the Falco custom settings."""
        logger.info("Removing Falco custom settings")

        # Remove all custom rules files
        for rule_file in self.falco_layout.rules_dir.glob("*.yaml"):
            rule_file.unlink()

        # Remove all custom config files
        for config_file in self.falco_layout.configs_dir.glob("*.yaml"):
            config_file.unlink()

        logger.info("Falco custom settings removed")

    def configure(self, charm_state: state.CharmState) -> None:
        """Configure the Falco custom settings.

        Args:
            charm_state (CharmState): The charm state
        """
        if not charm_state.custom_config_repo:
            logger.info("No custom config repository set")
            logger.debug("Removing Falco custom settings")
            self.remove()
            return

        logger.info("Configuring Falco custom settings")

        # Sync custom configuration repository
        _git_sync(
            str(charm_state.custom_config_repo),
            str(charm_state.custom_config_repo.host),
            ref=charm_state.custom_config_repo_ref,
            ssh_private_key=charm_state.custom_config_repo_ssh_key,
        )

        # Pull configuration files from the custom repository to falco config directories
        _pull_falco_rule_files(f"{self.falco_layout.rules_dir}/")
        _pull_falco_config_files(f"{self.falco_layout.configs_dir}/")

        logger.info("Falco custom settings configured")


class FalcoService:
    """Falco service manager."""

    def __init__(
        self,
        config_file: FalcoConfigFile,
        service_file: FalcoServiceFile,
        custom_setting: FalcoCustomSetting,
    ) -> None:
        self.config_file = config_file
        self.service_file = service_file
        self.custom_setting = custom_setting

    def install(self) -> None:
        """Install and configure the Falco service."""
        logger.info("Installing Falco service")

        self.config_file.install()
        self.service_file.install()
        self.custom_setting.install()

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
        self.custom_setting.remove()

        logger.info("Falco service removed")

    def configure(self, charm_state: state.CharmState) -> None:
        """Configure the Falco service.

        Args:
            charm_state (CharmState): The charm state
        Raises:
            FalcoConfigurationError: If configuration validation fails
        """
        logger.info("Configuring Falco service")

        try:
            self.custom_setting.configure(charm_state)
        except (GitCloneError, SshKeyScanError, RsyncError) as e:
            logger.error("Failed to configure Falco custom settings: %s", e)
            raise FalcoConfigurationError("Failed to configure Falco service") from e

        systemd.daemon_reload()
        systemd.service_restart(self.service_file.service_name)

        logger.info("Falco service configured and started")

    def check_active(self) -> bool:
        """Check if the Falco service is active."""
        return systemd.service_running(self.service_file.service_name)


def _pull_falco_rule_files(destination: str) -> None:
    """Pull falco config files from custom config repository.

    Args:
        destination (str): The destination directory for the pulled files

    Raises:
        RsyncError: If rsync fails
    """
    source = f"{CLONE_OUTPUT_DIR}/{FALCO_CUSTOM_RULES_KEY}/"
    rsync_cmd = [
        RSYNC,
        "-av",
        "--delete",
        "--include=*.yaml",
        source,
        destination,
    ]
    try:
        logger.error("Rsync command: %s", rsync_cmd)
        subprocess.run(rsync_cmd, check=True)
    except subprocess.CalledProcessError as e:
        logging.error("Rsync failed from %s to %s", source, destination)
        raise RsyncError(f"Rsync failed: {e.stderr}") from e


def _pull_falco_config_files(destination: str) -> None:
    """Pull falco config files from custom config repository.

    Args:
        destination (str): The destination directory for the pulled files

    Raises:
        RsyncError: If rsync fails
    """
    source = f"{CLONE_OUTPUT_DIR}/{FALCO_CUSTOM_CONFIGS_KEY}/"
    rsync_cmd = [
        RSYNC,
        "-av",
        "--delete",
        "--include=*.yaml",
        source,
        destination,
    ]
    try:
        subprocess.run(rsync_cmd, check=True)
    except subprocess.CalledProcessError as e:
        logging.error("Rsync failed from %s to %s", source, destination)
        raise RsyncError(f"Rsync failed: {e.stderr}") from e


def _git_sync(
    repo: str,
    hostname: str,
    ref: str = "",
    ssh_private_key: str = "",
) -> None:
    """Sync the repository to the specified destination.

    Args:
        repo (str): The repository URL
        hostname (str): The host to scan for Ssh key
        ref (str): The branch or tag to checkout
        ssh_private_key (str): The SSH private key content

    Raises:
        GitCloneError: If git clone fails
        SshKeyScanError: If ssh-keyscan fails
        SshKeyWriteError: If writing the Ssh key fails
    """
    repo_cloned = repo == _get_cloned_repo_url()
    repo_tag_matched = ref == _get_cloned_repo_tag()
    if repo_cloned and repo_tag_matched:
        logger.info("Custom config repository already synced")
        return

    if ssh_private_key:
        _setup_ssh_key(ssh_private_key)

    _add_known_hosts(hostname)
    _git_clone(repo, ref=ref)


def _setup_ssh_key(ssh_private_key: str) -> None:
    """Add the SSH private key to the host.

    Args:
        ssh_private_key (str): The SSH private key content

    Raises:
        SshKeyWriteError: If writing the Ssh key fails
    """
    try:
        with SSH_KEY_FILE.open("w", encoding="utf-8") as key_file:
            key_file.write(ssh_private_key)
        SSH_KEY_FILE.chmod(0o600)
    except OSError as e:
        logging.error("Error writing SSH private key to %s", SSH_KEY_FILE)
        raise SshKeyWriteError(f"Error writing SSH key to {SSH_KEY_FILE}") from e


def _add_known_hosts(hostname: str) -> None:
    """Scan and add the Ssh host key to known_hosts.

    Args:
        hostname (str): The host to scan

    Raises:
        SshKeyScanError: If ssh-keyscan fails
    """
    add_known_hosts_cmd = [SSH_KEYSCAN, "-t", "rsa", hostname]
    try:
        out = subprocess.check_output(add_known_hosts_cmd).decode()
        with KNOWN_HOSTS_FILE.open("w", encoding="utf-8") as known_hosts_file:
            known_hosts_file.write(out)
    except subprocess.CalledProcessError as e:
        logging.error("'%s' failed for host %s", SSH_KEYSCAN, hostname)
        raise SshKeyScanError(f"{SSH_KEYSCAN} failed for host {hostname}") from e
    except OSError as e:
        logging.error("Error writing to known hosts at %s", KNOWN_HOSTS_FILE)
        raise SshKeyScanError(f"Error writing to known hosts at {KNOWN_HOSTS_FILE}") from e


def _git_clone(repo: str, ref: str = "") -> None:
    """Clone a git repository using with depth 1.

    Args:
        repo (str): The repository URL
        ref (str): The branch or tag to checkout

    Raises:
        GitCloneError: If git clone fails
    """
    git_clone_cmd = [GIT, "clone", "--depth", "1", repo, str(CLONE_OUTPUT_DIR)]
    git_clone_cmd += ["-b", ref] if ref else []

    try:
        shutil.rmtree(CLONE_OUTPUT_DIR, ignore_errors=True)
        subprocess.run(git_clone_cmd, check=True)
    except subprocess.CalledProcessError as e:
        logging.error("Error cloning repository %s", repo)
        raise GitCloneError(f"Error cloning repository {repo}") from e


def _get_cloned_repo_url() -> str:
    """Get the cloned repository URL.

    Returns:
        The repository URL as a string or empty string if the repository is not cloned.
    """
    cmd = [GIT, "-C", str(CLONE_OUTPUT_DIR), "config", "--get", "remote.origin.url"]
    try:
        url = subprocess.check_output(cmd).decode()
    except subprocess.CalledProcessError as e:
        logger.debug(e)
        return ""
    return url.strip()


def _get_cloned_repo_tag() -> str:
    """Get the cloned repository tag.

    Returns:
        The repository tag as a string or empty string if the repository is not cloned.
    """
    cmd = [GIT, "-C", str(CLONE_OUTPUT_DIR), "describe", "--tags", "--exact-match"]
    try:
        tag = subprocess.check_output(cmd).decode()
    except subprocess.CalledProcessError as e:
        logger.debug(e)
        return ""
    return tag.strip()
