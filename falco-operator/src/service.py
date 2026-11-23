# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Falco workload management module."""

import hashlib
import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional

from charmlibs import systemd
from cosl import JujuTopology
from jinja2 import Environment, FileSystemLoader
from ops.charm import CharmBase
from ops.model import ProxyConfig

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
FALCOCTL_FOLLOW_SERVICE_NAME = "falcoctl-rules-follow"
OCI_RULES_FOLLOW_INTERVAL = "5m"
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
        """Get the staging directory for rules downloaded from OCI registries."""
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

    def install(self) -> bool:
        """Install template file.

        Returns:
            True if the destination file was created or changed.
        """
        return self._render(self.context)

    def remove(self) -> None:
        """Remove template file."""
        if self.destination.exists():
            self.destination.unlink()

    def _render(self, context: dict) -> bool:
        """Render template file from a template.

        Args:
            context (dict): Context for rendering the template

        Returns:
            True if the destination file was created or changed.

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
                return False
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
            return True
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

    def update(self, context: dict) -> bool:
        """Update the Falco service file with new context.

        Args:
            context: A dictionary containing new context values.

        Returns:
            True if the service file changed.
        """
        self.context.update(context)
        return self.install()


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

    A systemd service runs `falcoctl artifact follow` against a staging directory. The follow
    process checks the registry for changes and updates the staging directory. The charm then
    atomically copies changed rules into Falco's managed rules directory.
    """

    service_name = FALCOCTL_FOLLOW_SERVICE_NAME
    startup_timeout = OCI_RULES_STARTUP_TIMEOUT
    follow_interval = OCI_RULES_FOLLOW_INTERVAL

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
    def staging_dir(self) -> Path:
        """Get the directory used to stage OCI downloads and state."""
        return self.falco_layout.oci_rules_dir

    @property
    def config_file(self) -> Path:
        """Get the falcoctl configuration file used for OCI follows."""
        return self.staging_dir / "falcoctl.yaml"

    @property
    def rules_dir(self) -> Path:
        """Get the directory where falcoctl writes followed rules."""
        return self.staging_dir / "rules"

    @property
    def state_dir(self) -> Path:
        """Get the directory where falcoctl persists follow state."""
        return self.staging_dir / "follow-state"

    @property
    def plugins_dir(self) -> Path:
        """Get the staging directory for plugin dependencies."""
        return self.staging_dir / "plugins"

    @property
    def assets_dir(self) -> Path:
        """Get the staging directory for asset dependencies."""
        return self.staging_dir / "assets"

    @property
    def state_file(self) -> Path:
        """Get the file used to track the last installed OCI rules."""
        return self.staging_dir / "installed.json"

    def is_configured(self) -> bool:
        """Return whether the follow service has been configured."""
        return self.service_file.exists()

    def has_staging(self) -> bool:
        """Return whether an OCI staging directory is present."""
        return self.staging_dir.exists()

    def configure(self, username: str, password: str, oci_ref: str) -> bool:
        """Configure the falcoctl follow service and install any staged rules.

        Args:
            username: OCI registry username.
            password: OCI registry password or token.
            oci_ref: Full OCI artifact reference.

        Returns:
            True if the follow service or installed rules changed.

        Raises:
            OciRulesError: If the service cannot be configured or rules installed.
        """
        if not self.falco_layout.falcoctl_cmd.exists():
            raise OciRulesError(f"falcoctl binary not found at {self.falco_layout.falcoctl_cmd}")

        registry = _registry_from_oci_ref(oci_ref)
        staging_missing = not self.staging_dir.exists()
        try:
            self.staging_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
            os.chmod(self.staging_dir, 0o700)
            self.rules_dir.mkdir(parents=True, exist_ok=True)
            self.state_dir.mkdir(parents=True, exist_ok=True)
            self.plugins_dir.mkdir(parents=True, exist_ok=True)
            self.assets_dir.mkdir(parents=True, exist_ok=True)
            config_changed = self._write_config(registry, username, password)
            service_changed = self._render_service_file(oci_ref)
        except OSError as e:
            raise OciRulesError(f"Unable to prepare OCI rules staging directory: {e}") from e

        if service_changed or config_changed or staging_missing:
            if systemd.service_running(self.service_name):
                systemd.service_stop(self.service_name)
            shutil.rmtree(self.rules_dir, ignore_errors=True)
            self.rules_dir.mkdir(parents=True, exist_ok=True)
            shutil.rmtree(self.state_dir, ignore_errors=True)
            self.state_dir.mkdir(parents=True, exist_ok=True)

        if service_changed:
            systemd.daemon_reload()

        systemd.service_enable(self.service_name)
        service_running = systemd.service_running(self.service_name)
        if service_changed or config_changed or staging_missing or not service_running:
            systemd.service_restart(self.service_name)

        self._wait_for_staged_rules()
        rules_changed = self.sync_staged_rules(oci_ref)
        return (
            service_changed
            or config_changed
            or staging_missing
            or not service_running
            or rules_changed
        )

    def sync_staged_rules(self, oci_ref: str) -> bool:
        """Atomically install staged rules when they changed.

        Args:
            oci_ref: Full OCI artifact reference associated with the staged rules.

        Returns:
            True if the installed rules changed.
        """
        rule_files = self._staged_rule_files()
        if not rule_files:
            logger.warning("No staged OCI rules available to install")
            return False

        digest = _digest_rule_files(rule_files)
        previous_state = self._read_state()
        previous_files = previous_state.get("files", [])
        if (
            previous_state.get("ref") == oci_ref
            and previous_state.get("digest") == digest
            and all((self.falco_layout.rules_dir / name).exists() for name in previous_files)
        ):
            logger.debug("OCI rules from %s are already up to date", oci_ref)
            return False

        try:
            self._install_rules(rule_files)
            self._remove_stale_rules(previous_files, [rule_file.name for rule_file in rule_files])
            self._write_state(
                {
                    "ref": oci_ref,
                    "digest": digest,
                    "files": [rule_file.name for rule_file in rule_files],
                }
            )
        except OSError as e:
            raise OciRulesError(f"Unable to install OCI rules: {e}") from e

        logger.info("Installed %d rule file(s) from %s", len(rule_files), oci_ref)
        return True

    def remove(self) -> bool:
        """Stop the follow service and remove OCI rules, state, and staging files.

        Returns:
            True if anything was removed.
        """
        removed = False
        if self.service_file.exists():
            systemd.service_stop(self.service_name)
            systemd.service_disable(self.service_name)
            self.service_file.unlink()
            systemd.daemon_reload()
            removed = True

        state = self._read_state()
        for name in state.get("files", []):
            path = self.falco_layout.rules_dir / name
            if path.exists():
                path.unlink()
                removed = True

        if self.staging_dir.exists():
            shutil.rmtree(self.staging_dir, ignore_errors=True)
            removed = True

        return removed

    def _render_service_file(self, oci_ref: str) -> bool:
        """Render the falcoctl follow systemd unit.

        Args:
            oci_ref: Full OCI artifact reference to follow.

        Returns:
            True if the unit file changed.
        """
        template = Template(
            "falcoctl-follow.service.j2",
            self.service_file,
            {
                "falcoctl": str(self.falco_layout.falcoctl_cmd),
                "config_file": str(self.config_file),
                "rules_dir": str(self.rules_dir),
                "plugins_dir": str(self.plugins_dir),
                "assets_dir": str(self.assets_dir),
                "state_dir": str(self.state_dir),
                "falco_versions": "http://127.0.0.1:8765/versions",
                "every": self.follow_interval,
                "oci_ref": oci_ref,
            },
        )
        return template.install()

    def _write_config(self, registry: str, username: str, password: str) -> bool:
        """Write a mode-0600 falcoctl config with registry credentials.

        Args:
            registry: OCI registry hostname.
            username: OCI registry username.
            password: OCI registry password or token.

        Returns:
            True if the configuration file changed.
        """
        credentials_file = self.staging_dir / "credentials.json"
        config = (
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

    def _wait_for_staged_rules(self) -> None:
        """Wait briefly for the follow service to populate the staging directory."""
        deadline = time.monotonic() + self.startup_timeout
        while time.monotonic() < deadline:
            if self._staged_rule_files():
                return
            time.sleep(1)
        logger.warning("No staged OCI rules appeared within %s seconds", self.startup_timeout)

    def _staged_rule_files(self) -> list[Path]:
        """Return YAML rule files currently present in staging."""
        return sorted(
            list(self.rules_dir.glob("*.yaml")) + list(self.rules_dir.glob("*.yml")),
            key=lambda path: path.name,
        )

    def _install_rules(self, rule_files: list[Path]) -> None:
        """Atomically copy staged rules into Falco's managed rules directory.

        Args:
            rule_files: Rule files read from the staging directory.
        """
        self.falco_layout.rules_dir.mkdir(parents=True, exist_ok=True)
        for rule_file in rule_files:
            data = rule_file.read_bytes()
            temp_path = None
            try:
                with tempfile.NamedTemporaryFile(
                    dir=self.falco_layout.rules_dir,
                    prefix=f".{rule_file.name}.",
                    suffix=".tmp",
                    delete=False,
                ) as temp_file:
                    temp_file.write(data)
                    temp_path = Path(temp_file.name)
                os.chmod(temp_path, 0o644)
                os.replace(temp_path, self.falco_layout.rules_dir / rule_file.name)
            finally:
                if temp_path and temp_path.exists():
                    temp_path.unlink()

    def _remove_stale_rules(self, previous_files: list[str], current_files: list[str]) -> None:
        """Remove files that were part of the previous artifact but are no longer present.

        Args:
            previous_files: File names installed by the previous OCI artifact.
            current_files: File names installed by the current OCI artifact.
        """
        for name in set(previous_files) - set(current_files):
            path = self.falco_layout.rules_dir / name
            if path.exists():
                path.unlink()

    def _read_state(self) -> dict:
        """Read the OCI rules state.

        Returns:
            The state mapping, or an empty mapping if it is missing or invalid.
        """
        if not self.state_file.exists():
            return {}
        try:
            return json.loads(self.state_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Unable to read OCI rules state from %s: %s", self.state_file, e)
            return {}

    def _write_state(self, state: dict) -> None:
        """Write the OCI rules state.

        Args:
            state: State mapping to persist.
        """
        temp_path = self.state_file.with_name(self.state_file.name + ".tmp")
        fd = os.open(temp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as state_file:
            json.dump(state, state_file, indent=2)
            state_file.write("\n")
        os.replace(temp_path, self.state_file)


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


def _digest_rule_files(rule_files: list[Path]) -> str:
    """Compute a stable digest of the extracted rule files.

    Args:
        rule_files: Rule files to hash.

    Returns:
        Hex-encoded SHA256 digest.
    """
    digest = hashlib.sha256()
    for rule_file in sorted(rule_files, key=lambda path: path.name):
        digest.update(rule_file.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(rule_file.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


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
            True if any rule, config, or OCI staging state was removed.
        """
        logger.info("Removing Falco custom settings")
        removed = False

        # Remove all custom rules files
        for rule_file in [
            *self.falco_layout.rules_dir.glob("*.yaml"),
            *self.falco_layout.rules_dir.glob("*.yml"),
        ]:
            rule_file.unlink()
            removed = True

        # Remove OCI staging state
        removed = self.oci_rules.remove() or removed

        # Remove all custom config files
        for config_file in self.falco_layout.configs_dir.glob("*.yaml"):
            config_file.unlink()
            removed = True

        logger.info("Falco custom settings removed")
        return removed

    def configure(self, charm_state: state.CharmState) -> bool:
        """Configure the Falco custom settings.

        Args:
            charm_state (CharmState): The charm state

        Returns:
            True if the rules or configuration changed and Falco should be restarted.

        Raises:
            OciRulesError: If OCI rules cannot be fetched or installed.
        """
        if charm_state.custom_rules_oci_ref:
            return self._configure_oci_rules(charm_state)

        oci_rules_configured = self.oci_rules.has_staging()
        oci_rules_removed = self.oci_rules.remove()

        if not charm_state.custom_config_repo:
            logger.info("No custom rules source set")
            logger.debug("Removing Falco custom settings")
            return self.remove() or oci_rules_removed

        logger.info("Configuring Falco custom settings")

        # A previous OCI rules installation may not have a complete state file. Clear the
        # managed rules before switching back to the git source.
        if oci_rules_configured:
            self.remove()

        # Sync custom configuration repository
        git_changed = _git_sync(
            str(charm_state.custom_config_repo),
            str(charm_state.custom_config_repo.host),
            ref=charm_state.custom_config_repo_ref,
            ssh_private_key=charm_state.custom_config_repo_ssh_key,
        )

        # Pull configuration files from the custom repository to falco config directories
        _pull_falco_rule_files(f"{self.falco_layout.rules_dir}/")
        _pull_falco_config_files(f"{self.falco_layout.configs_dir}/")

        logger.info("Falco custom settings configured")
        return git_changed or oci_rules_removed

    def _configure_oci_rules(self, charm_state: state.CharmState) -> bool:
        """Configure custom rules from an OCI registry.

        Args:
            charm_state: The charm state.

        Returns:
            True if the rules changed and Falco should be restarted.
        """
        # The first OCI reconciliation must remove rules installed by the git source.
        if not self.oci_rules.is_configured():
            self.remove()

        return self.oci_rules.configure(
            username=charm_state.custom_rules_username or "",
            password=charm_state.custom_rules_password or "",
            oci_ref=charm_state.custom_rules_oci_ref or "",
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
            changed = self.custom_setting.configure(charm_state)
            self.proxy_env_file.install()
            service_file_changed = self.service_file.update(
                context={"http_output": charm_state.http_output}
            )
        except (GitCloneError, SshKeyScanError, RsyncError, OciRulesError) as e:
            logger.error("Failed to configure Falco custom settings: %s", e)
            raise FalcoConfigurationError("Failed to configure Falco service") from e

        systemd.daemon_reload()
        if changed or service_file_changed or not self.check_active():
            systemd.service_restart(self.service_file.service_name)

        logger.info("Falco service configured")

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
) -> bool:
    """Sync the repository to the specified destination.

    Args:
        repo (str): The repository URL
        hostname (str): The host to scan for Ssh key
        ref (str): The branch or tag to checkout
        ssh_private_key (str): The SSH private key content

    Returns:
        True if the repository was cloned or updated, False if it was already synced.

    Raises:
        GitCloneError: If git clone fails
        SshKeyScanError: If ssh-keyscan fails
        SshKeyWriteError: If writing the Ssh key fails
    """
    repo_cloned = repo == _get_cloned_repo_url()
    repo_tag_matched = ref == _get_cloned_repo_tag()
    if repo_cloned and repo_tag_matched:
        logger.info("Custom config repository already synced")
        return False

    if ssh_private_key:
        _setup_ssh_key(ssh_private_key)

    _add_known_hosts(hostname)
    _git_clone(repo, ref=ref)
    return True


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
