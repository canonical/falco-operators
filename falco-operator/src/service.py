# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Falco workload management module."""

import json
import logging
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional

from charmlibs import systemd
from cosl import JujuTopology
from jinja2 import Environment, FileSystemLoader
from ops.charm import CharmBase
from ops.model import ProxyConfig

import state
from config import DEFAULT_FOLLOW_INTERVAL

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
FALCOCTL_FOLLOW_SERVICE_NAME = "falcoctl-rules-follow"
OCI_RULES_STARTUP_TIMEOUT = 60

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


class OciRulesError(Exception):
    """Exception raised when OCI rules cannot be fetched or installed."""


class FalcoLayout:
    """Falco file layout.

    These are constant paths defined in the `charmcraft.yaml`, and they are created when the charm
    packs. Also see `.github/workflows/build_falco.yaml`.
    """

    _cmd: Path = Path("usr/bin/falco")
    _falcoctl_cmd: Path = Path("usr/bin/falcoctl")
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
    def falcoctl_cmd(self) -> Path:
        """Get the full path to the falcoctl command."""
        return self.home / self._falcoctl_cmd

    @property
    def oci_rules_dir(self) -> Path:
        """Get the directory for OCI rules configuration and follow state."""
        return self.home / "etc/falco/oci-rules"

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

    @property
    def proxy_env_file(self) -> Path:
        """Get the full path to the Falco proxy environment file."""
        return self.config_file.parent / "proxy.env"


class Template:
    """Template file manager."""

    def __init__(
        self,
        name: str,
        destination: Path,
        context: Optional[dict],
        mode: Optional[int] = None,
    ) -> None:
        """Initialize the template file manager.

        Args:
            name (str): Template file name
            destination (Path): Destination path for the rendered template
            context (Optional[dict]): Context for rendering the template
            mode (Optional[int]): File mode for the rendered file. If omitted, the
                file is written with the process umask.
        """
        self.name = name
        self.destination = destination
        self.context = context or {}
        self.mode = mode

        # These templates render systemd and YAML files, not HTML. Enabling
        # autoescape would corrupt values such as proxy URLs containing "&".
        self._env = Environment(  # nosec B701
            loader=FileSystemLoader(TEMPLATE_DIR),
            autoescape=False,  # noqa: S701
        )
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
            if (
                self.destination.exists()
                and self.destination.read_text(encoding="utf-8") == content
            ):
                logger.debug("Template file unchanged at %s", self.destination)
                return
            if not self.destination.parent.exists():
                self.destination.parent.mkdir(parents=True, exist_ok=True)
            if self.mode is None:
                self.destination.write_text(content, encoding="utf-8")
            else:
                file_descriptor = os.open(
                    self.destination, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, self.mode
                )
                with os.fdopen(file_descriptor, "w", encoding="utf-8") as destination_file:
                    destination_file.write(content)
                self.destination.chmod(self.mode)
            logger.debug("Template file generated at %s", self.destination)
        except OSError as e:
            logger.exception("Failed to write template to %s", self.destination)
            raise TemplateRenderError(f"Failed to write template to {self.destination}") from e


class FalcoServiceFile(Template):
    """Falco systemd unit file manager."""

    service_name = FALCO_SERVICE_NAME
    template: str = "falco.service.j2"
    service_file: Path = SYSTEMD_SERVICE_DIR / f"{FALCO_SERVICE_NAME}.service"

    def __init__(self, falco_layout: FalcoLayout, charm: CharmBase) -> None:
        """Initialize the Falco service file manager.

        Args:
            falco_layout: The Falco file layout.
            charm: The charm instance.
        """
        context = {
            "command": str(falco_layout.cmd),
            "rules_dir": str(falco_layout.rules_dir),
            "config_file": str(falco_layout.config_file),
            "falco_home": str(falco_layout.home),
            "juju_topology": JujuTopology.from_charm(charm).as_dict(),
            "proxy_env_file": str(falco_layout.proxy_env_file),
        }
        super().__init__(self.template, self.service_file, context=context)

    def update(self, context: dict) -> None:
        """Update the Falco service file with new context.

        Args:
            context: A dictionary containing new context values.
        """
        self.context.update(context)
        self.install()


class FalcoProxyEnvFile(Template):
    """Falco proxy environment file manager."""

    template: str = "proxy.env.j2"

    def __init__(self, falco_layout: FalcoLayout, proxy_config: ProxyConfig) -> None:
        """Initialize the Falco proxy environment file manager.

        Args:
            falco_layout: The Falco file layout.
            proxy_config: The model's proxy configuration.
        """
        http_proxy = proxy_config.http or ""
        https_proxy = proxy_config.https or ""
        no_proxy = ",".join(proxy_config.no)
        proxy_values = [
            ("HTTP_PROXY", http_proxy),
            ("http_proxy", http_proxy),
            ("HTTPS_PROXY", https_proxy),
            ("https_proxy", https_proxy),
            ("NO_PROXY", no_proxy),
            ("no_proxy", no_proxy),
        ]
        super().__init__(
            self.template,
            falco_layout.proxy_env_file,
            context={"proxy_values": [(key, value) for key, value in proxy_values if value]},
            mode=0o600,
        )

    def install(self) -> None:
        """Install the proxy environment file, or remove it if unset."""
        if not self.context["proxy_values"]:
            self.remove()
            return
        super().install()


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


class FalcoOciRules:
    """Manage Falco rules fetched from an OCI registry with falcoctl.

    A systemd service runs `falcoctl artifact follow` directly against Falco's managed rules
    directory. On configuration or secret changes, the charm clears the managed rules and
    restarts the follower so the current artifact is installed from scratch.
    """

    service_name = FALCOCTL_FOLLOW_SERVICE_NAME
    startup_timeout = OCI_RULES_STARTUP_TIMEOUT

    def __init__(
        self,
        falco_layout: FalcoLayout,
        systemd_service_dir: Path = SYSTEMD_SERVICE_DIR,
    ) -> None:
        """Initialize the OCI rules manager.

        Args:
            falco_layout: The Falco file layout.
            systemd_service_dir: Directory where the follow service unit is written.
        """
        self.falco_layout = falco_layout
        self.service_file = systemd_service_dir / f"{self.service_name}.service"

    @property
    def oci_rules_dir(self) -> Path:
        """Get the directory used to store falcoctl configuration and state."""
        return self.falco_layout.oci_rules_dir

    @property
    def config_file(self) -> Path:
        """Get the falcoctl configuration file used for OCI follows."""
        return self.oci_rules_dir / "falcoctl.yaml"

    @property
    def state_dir(self) -> Path:
        """Get the directory where falcoctl persists follow state."""
        return self.oci_rules_dir / "follow-state"

    @property
    def tmp_dir(self) -> Path:
        """Get the temporary directory used by falcoctl for atomic file moves."""
        return self.oci_rules_dir / "tmp"

    @property
    def rules_dir(self) -> Path:
        """Get Falco's managed rules directory."""
        return self.falco_layout.rules_dir

    def is_configured(self) -> bool:
        """Return whether the OCI rules source has been configured."""
        return self.service_file.exists() or self.config_file.exists()

    def has_oci_state(self) -> bool:
        """Return whether any OCI rules state or the follow service is present.

        The unit file and the state directory live in different locations and can be left
        behind independently, so either one means the OCI source still needs cleanup.
        """
        return self.service_file.exists() or self.oci_rules_dir.exists()

    def configure(
        self,
        username: str,
        password: str,
        oci_ref: str,
        follow_interval: str = DEFAULT_FOLLOW_INTERVAL,
    ) -> None:
        """Configure OCI rules and the falcoctl follow service.

        On configuration changes, existing managed rules are removed and the artifact is
        installed from scratch.

        Args:
            username: OCI registry username.
            password: OCI registry password or token.
            oci_ref: Full OCI artifact reference.
            follow_interval: Go duration for registry checks.

        Raises:
            OciRulesError: If the rules cannot be configured or installed.
        """
        if not self.falco_layout.falcoctl_cmd.exists():
            raise OciRulesError(f"falcoctl binary not found at {self.falco_layout.falcoctl_cmd}")

        follow_interval = follow_interval or DEFAULT_FOLLOW_INTERVAL
        registry = _registry_from_oci_ref(oci_ref)
        state_missing = not self.oci_rules_dir.exists()
        try:
            self.oci_rules_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
            # mkdir applies the umask and does not change an existing directory, so enforce
            # the mode explicitly. The directory holds registry credentials and follow state.
            os.chmod(self.oci_rules_dir, 0o700)
            self.state_dir.mkdir(parents=True, exist_ok=True)
            self.tmp_dir.mkdir(parents=True, exist_ok=True)
            config_changed = self._write_config(registry, username, password)
            service_changed = self._render_service_file(oci_ref, follow_interval)
        except OSError as e:
            raise OciRulesError(f"Unable to prepare OCI rules directory: {e}") from e

        # Reinstall from scratch when the unit or credentials changed, the state directory
        # disappeared, or the follower is not running.
        service_running = systemd.service_running(self.service_name)
        reset_required = service_changed or config_changed or state_missing or not service_running

        if reset_required:
            if service_running:
                # Stop the follower before deleting rules so it cannot write while we clear them.
                systemd.service_stop(self.service_name)
            # falcoctl follow does not delete destination files that are absent from the new
            # artifact, so clear the managed rules before a fresh install.
            self._clear_rules()
            # The follow state caches the last artifact digest. If it survives the rule reset,
            # falcoctl may consider the artifact installed and skip copying the files.
            shutil.rmtree(self.state_dir, ignore_errors=True)
            self.state_dir.mkdir(parents=True, exist_ok=True)
            # Remove leftovers from an interrupted run; this directory is used for the
            # temporary files that falcoctl atomically moves into rules.d.
            shutil.rmtree(self.tmp_dir, ignore_errors=True)
            self.tmp_dir.mkdir(parents=True, exist_ok=True)

        if service_changed:
            systemd.daemon_reload()

        systemd.service_enable(self.service_name)
        if reset_required:
            systemd.service_restart(self.service_name)
            self._wait_for_rules()

    def remove(self) -> bool:
        """Stop the follow service and remove OCI rules state.

        Returns:
            True if anything was removed.
        """
        removed = False
        # Only clear managed rules when OCI rules may have been installed, so removing the
        # OCI source does not delete rules managed by the git source.
        oci_configured = self.has_oci_state()
        if self.service_file.exists():
            systemd.service_stop(self.service_name)
            systemd.service_disable(self.service_name)
            self.service_file.unlink()
            systemd.daemon_reload()
            removed = True

        if oci_configured:
            removed = self._clear_rules() or removed

        if self.oci_rules_dir.exists():
            shutil.rmtree(self.oci_rules_dir, ignore_errors=True)
            removed = True

        return removed

    def _clear_rules(self) -> bool:
        """Remove all YAML rules from Falco's managed rules directory.

        Returns:
            True if any rule files were removed.
        """
        removed = False
        for rule_file in self._rule_files():
            rule_file.unlink()
            removed = True
        return removed

    def _render_service_file(self, oci_ref: str, follow_interval: str) -> bool:
        """Render the falcoctl follow systemd unit.

        Args:
            oci_ref: Full OCI artifact reference to follow.
            follow_interval: Interval between registry checks.

        Returns:
            True if the unit file changed.
        """
        previous_content = (
            self.service_file.read_text(encoding="utf-8") if self.service_file.exists() else None
        )
        template = Template(
            "falcoctl-follow.service.j2",
            self.service_file,
            {
                "falcoctl": str(self.falco_layout.falcoctl_cmd),
                "config_file": str(self.config_file),
                "rules_dir": str(self.rules_dir),
                "state_dir": str(self.state_dir),
                "tmp_dir": str(self.tmp_dir),
                "falco_versions": "http://127.0.0.1:8765/versions",
                "every": follow_interval,
                "oci_ref": oci_ref,
            },
        )
        template.install()
        current_content = self.service_file.read_text(encoding="utf-8")
        return current_content != previous_content

    def _write_config(self, registry: str, username: str, password: str) -> bool:
        """Write a mode-0600 falcoctl config with registry credentials.

        Args:
            registry: OCI registry hostname.
            username: OCI registry username.
            password: OCI registry password or token.

        Returns:
            True if the configuration file changed.
        """
        credentials_file = self.oci_rules_dir / "credentials.json"
        config = (
            "indexes: []\n"
            "registry:\n"
            "  creds:\n"
            f"    config: {json.dumps(str(credentials_file))}\n"
            "  auth:\n"
            "    basic:\n"
            f"      - registry: {json.dumps(registry)}\n"
            f"        user: {json.dumps(username)}\n"
            f"        password: {json.dumps(password)}\n"
        )
        if self.config_file.exists() and self.config_file.read_text(encoding="utf-8") == config:
            return False
        fd = os.open(self.config_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as config_file:
            config_file.write(config)
        os.chmod(self.config_file, 0o600)
        return True

    def _wait_for_rules(self) -> None:
        """Wait briefly for the follow service to populate the managed rules directory."""
        deadline = time.monotonic() + self.startup_timeout
        while time.monotonic() < deadline:
            if self._rule_files():
                return
            time.sleep(1)
        logger.warning("No OCI rules appeared within %s seconds", self.startup_timeout)

    def _rule_files(self) -> list[Path]:
        """Return YAML rule files currently present in the managed rules directory."""
        return sorted(
            list(self.rules_dir.glob("*.yaml")) + list(self.rules_dir.glob("*.yml")),
            key=lambda path: path.name,
        )


def _registry_from_oci_ref(oci_ref: str) -> str:
    """Extract the registry hostname from an OCI reference.

    Args:
        oci_ref: Full OCI artifact reference.

    Returns:
        The registry hostname.

    Raises:
        OciRulesError: If the reference is not a full OCI reference.
    """
    if "://" in oci_ref:
        raise OciRulesError("OCI reference must not include a URL scheme")
    registry, separator, _ = oci_ref.partition("/")
    if not separator or not registry:
        raise OciRulesError("OCI reference must include a registry and repository")
    return registry


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
        self.oci_rules = FalcoOciRules(falco_layout)

    def install(self) -> None:
        """Install the Falco custom settings."""
        logger.info("Installing Falco custom settings")

        # Ensure the custom rules and config directories exist
        self.falco_layout.rules_dir.mkdir(parents=True, exist_ok=True)
        self.falco_layout.configs_dir.mkdir(parents=True, exist_ok=True)

        # Ensure SSH directory exists
        SSH_DIR.mkdir(mode=0o700, exist_ok=True)

        logger.info("Falco custom settings installed")

    def remove(self) -> bool:
        """Remove the Falco custom settings.

        Returns:
            True if any rule, config, or OCI rules state was removed.
        """
        logger.info("Removing Falco custom settings")

        # Stop the OCI follower before changing the managed rules directory.
        removed = self.oci_rules.remove()

        # Remove all custom rules files
        for rule_file in [
            *self.falco_layout.rules_dir.glob("*.yaml"),
            *self.falco_layout.rules_dir.glob("*.yml"),
        ]:
            rule_file.unlink()
            removed = True

        # Remove all custom config files
        for config_file in self.falco_layout.configs_dir.glob("*.yaml"):
            config_file.unlink()
            removed = True

        logger.info("Falco custom settings removed")
        return removed

    def configure(self, charm_state: state.CharmState) -> None:
        """Configure the Falco custom settings.

        Args:
            charm_state (CharmState): The charm state

        Raises:
            OciRulesError: If OCI rules cannot be fetched or installed.
        """
        if charm_state.custom_rules_oci_ref:
            self._configure_oci_rules(charm_state)
            return

        oci_rules_configured = self.oci_rules.has_oci_state()
        self.oci_rules.remove()

        if not charm_state.custom_config_repo:
            logger.info("No custom rules source set")
            logger.debug("Removing Falco custom settings")
            self.remove()
            return

        logger.info("Configuring Falco custom settings")

        # A previous OCI rules installation may not have a complete state file. Clear the
        # managed rules before switching back to the git source.
        if oci_rules_configured:
            self.remove()

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

    def _configure_oci_rules(self, charm_state: state.CharmState) -> None:
        """Configure custom rules from an OCI registry.

        Args:
            charm_state: The charm state.
        """
        # The first OCI reconciliation must remove rules installed by the git source.
        if not self.oci_rules.is_configured():
            self.remove()

        self.oci_rules.configure(
            username=charm_state.custom_rules_username or "",
            password=charm_state.custom_rules_password or "",
            oci_ref=charm_state.custom_rules_oci_ref or "",
            follow_interval=charm_state.custom_rules_follow_interval,
        )


class FalcoService:
    """Falco service manager."""

    def __init__(
        self,
        config_file: FalcoConfigFile,
        service_file: FalcoServiceFile,
        proxy_env_file: FalcoProxyEnvFile,
        custom_setting: FalcoCustomSetting,
    ) -> None:
        self.config_file = config_file
        self.service_file = service_file
        self.proxy_env_file = proxy_env_file
        self.custom_setting = custom_setting

    def install(self) -> None:
        """Install and configure the Falco service."""
        logger.info("Installing Falco service")

        self.config_file.install()
        self.proxy_env_file.install()
        self.service_file.install()
        self.custom_setting.install()

        systemd.service_enable(self.service_file.service_name)
        systemd.service_start(self.service_file.service_name)

        logger.info("Falco service installed")

    def remove(self) -> None:
        """Remove the Falco service and clean up files."""
        logger.info("Removing Falco service")

        systemd.service_stop(self.service_file.service_name)
        systemd.service_disable(self.service_file.service_name)
        systemd.daemon_reload()

        self.config_file.remove()
        self.proxy_env_file.remove()
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
            self.proxy_env_file.install()
            self.service_file.update(context={"http_output": charm_state.http_output})
        except (GitCloneError, SshKeyScanError, RsyncError, OciRulesError) as e:
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
        "--",
        source,
        destination,
    ]
    try:
        logger.debug("Rsync command: %s", rsync_cmd)
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
        "--",
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
        fd = os.open(SSH_KEY_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as key_file:
            key_file.write(ssh_private_key)
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
