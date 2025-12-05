# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm config option module."""

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import ops
from pydantic import AnyUrl, BaseModel, ValidationError, field_validator

from service import FalcoLayout

logger = logging.getLogger(__name__)

# Executable paths
GIT = "/usr/bin/git"
RSYNC = "/usr/bin/rsync"
SSH_KEYSCAN = "/usr/bin/ssh-keyscan"

# Ssh related paths
Ssh_DIR = Path.home() / ".ssh"
SSH_KEY_FILE = Ssh_DIR / "id_rsa_falco_setting_repo"
KNOWN_HOSTS_FILE = Ssh_DIR / "known_hosts"

# Keys to look for in the setting repo.
# See `setting-repo` config option in `charmcraft.yaml` to learn more.
RSYNC_CUSTOM_RULES_KEY = "rules.d"
RSYNC_CUSTOM_CONFIGS_KEY = "config.override.d"

# Supported URL schemes for setting-repo
SUPPORTED_URL_SCHEMES = "git+ssh"


class RsyncError(Exception):
    """Exception raised when rsync fails."""


class GitCloneError(Exception):
    """Exception raised when git clone fails."""


class SshKeyScanError(Exception):
    """Exception raised when Ssh keyscan fails."""


class SshKeyWriteError(Exception):
    """Exception raised when writing Ssh key fails."""


class CharmConfig(BaseModel):
    """Model for validating charm configuration options."""

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True

    setting_repo: str = ""
    setting_repo_ssh_key_id: Optional[ops.Secret] = None

    @field_validator("setting_repo")
    @classmethod
    def validate_setting_repo(cls, v: str) -> str:
        """Validate the setting_repo URL.

        Args:
            v (str): The setting_repo URL

        Returns:
            The validated setting_repo URL

        Raises:
            ValueError: If the URL is invalid
        """
        # No need to validate for empty URL
        if not v:
            return v

        try:
            url = AnyUrl(v)
        except ValidationError as e:
            raise ValueError(f"Invalid setting repo URL: {v}") from e

        if url.scheme not in SUPPORTED_URL_SCHEMES:
            raise ValueError(f"Only {SUPPORTED_URL_SCHEMES} are supported")
        return v


class SettingRepoManager:
    """Manager for handling custom falco setting repository."""

    working_dir: Path = Path.home() / "falco_setting_repo"

    def __init__(self, model: ops.Model, charm_config: CharmConfig) -> None:
        """Initialize the SettingRepoManager.

        Args:
            model (Model): The Juju model instance
            charm_config (CharmConfig): The CharmConfig instance
        """
        self.model = model
        self.charm_config = charm_config
        self._setting_repo = AnyUrl(charm_config.setting_repo)

    @property
    def url(self) -> str:
        """Get the URL of the repository.

        Returns:
            The repository URL as a string
        """
        return str(self._setting_repo).replace(f"?{self._setting_repo.query}", "")

    @property
    def ref(self) -> str:
        """Get the reference (branch or tag) of the repository.

        Returns:
            The reference as a string or empty string if not specified
        """
        return dict(self._setting_repo.query_params()).get("ref", "").lstrip("/")

    @property
    def host(self) -> str:
        """Get the host of the repository.

        Returns:
            The repository host as a string
        """
        return self._setting_repo.host or ""

    @property
    def sub_path(self) -> Optional[str]:
        """Get the sub-path within the repository.

        Returns:
            The sub-path as a string
        """
        return dict(self._setting_repo.query_params()).get("sub_path", "")

    @property
    def ssh_private_key(self) -> str:
        """Get the Ssh private key content.

        Returns:
            The Ssh private key content as a string
        """
        if not self.charm_config.setting_repo_ssh_key_id:
            return ""

        ssh_key_id = self.charm_config.setting_repo_ssh_key_id.id
        ssh_key_secret = self.model.get_secret(id=ssh_key_id)
        ssh_key_content = ssh_key_secret.get_content(refresh=True)
        return ssh_key_content.get("value", "")

    def sync(self, falco_layout: FalcoLayout) -> bool:
        """Clone the setting repository to the specified destination.

        Args:
            falco_layout (FalcoLayout): The FalcoLayout instance

        Returns:
            True if the repository was already synced or synced successfully, False otherwise
        """
        repo_cloned = self.url == self._get_cloned_repo_url()
        repo_ref_matched = self.ref == self._get_cloned_repo_ref()
        if repo_cloned and repo_ref_matched:
            logger.info("Setting repository already synced")
            return True

        if not self.url or not self.host:
            return False

        self._add_ssh_key()
        self._add_known_hosts()

        if self.working_dir.exists():
            shutil.rmtree(self.working_dir)

        self._git_clone()

        sub_path = self.sub_path or ""
        rules_dir = self.working_dir / sub_path / RSYNC_CUSTOM_RULES_KEY
        configs_dir = self.working_dir / sub_path / RSYNC_CUSTOM_CONFIGS_KEY
        if rules_dir.exists():
            self._rsync(f"{rules_dir}/", f"{falco_layout.rules_dir}/")
        if configs_dir.exists():
            self._rsync(f"{configs_dir}/", f"{falco_layout.configs_dir}/")
        return True

    def _rsync(self, source: str, destination: str) -> None:
        """Rsync files from source to destination.

        Args:
            source (str): The source directory
            destination (str): The destination directory

        Raises:
            RsyncError: If rsync fails
        """
        rsync_cmd = [RSYNC, "-av", "--delete", source, destination]
        try:
            subprocess.run(rsync_cmd, check=True)
        except subprocess.CalledProcessError as e:
            logging.exception("Rsync failed from %s to %s", source, destination)
            raise RsyncError(f"Rsync failed: {e.stderr}") from e

    def _add_ssh_key(self) -> None:
        """Add the Ssh private key to the host.

        Raises:
            SshKeyWriteError: If writing the Ssh key fails
        """
        Ssh_DIR.mkdir(mode=0o700, exist_ok=True)
        try:
            with SSH_KEY_FILE.open("w", encoding="utf-8") as key_file:
                key_file.write(self.ssh_private_key)
            SSH_KEY_FILE.chmod(0o600)
        except OSError as e:
            logging.exception("Error writing Ssh key to %s", SSH_KEY_FILE)
            raise SshKeyWriteError(f"Error writing Ssh key to {SSH_KEY_FILE}") from e

    def _add_known_hosts(self) -> None:
        """Scan and add the Ssh host key to known_hosts.

        Raises:
            SshKeyScanError: If ssh-keyscan fails
        """
        add_known_hosts_cmd = [SSH_KEYSCAN, "-t", "rsa", self.host]
        try:
            out = subprocess.check_output(add_known_hosts_cmd).decode()
            with KNOWN_HOSTS_FILE.open("w", encoding="utf-8") as known_hosts_file:
                known_hosts_file.write(out)
        except subprocess.CalledProcessError as e:
            logging.exception("Ssh keyscan failed for host %s", self.host)
            raise SshKeyScanError(f"Ssh keyscan failed: {e.stderr}") from e
        except OSError as e:
            logging.exception("Error writing to known_hosts at %s", KNOWN_HOSTS_FILE)
            raise SshKeyScanError(f"Error writing to known_hosts at {KNOWN_HOSTS_FILE}") from e

    def _git_clone(self) -> None:
        """Clone a git repository using git+ssh scheme with depth 1.

        Raises:
            GitCloneError: If git clone fails
        """
        git_clone_cmd = [GIT, "clone", "--depth", "1", self.url, str(self.working_dir)]
        git_clone_cmd += ["--branch", self.ref] if self.ref else []

        try:
            subprocess.run(git_clone_cmd, check=True)
        except subprocess.CalledProcessError as e:
            logging.exception("Git clone of repository failed for repo %s", self.working_dir)
            raise GitCloneError(f"Git clone of setting repository failed: {e}") from e

    def _get_cloned_repo_url(self) -> str:
        """Get the cloned repository URL.

        Returns:
            The repository URL as a string or empty string if the repository is not cloned.
        """
        cmd = [GIT, "-C", str(self.working_dir), "config", "--get", "remote.origin.url"]
        try:
            url = subprocess.check_output(cmd).decode()
        except subprocess.CalledProcessError as e:
            logger.debug(e)
            return ""
        return url.strip()

    def _get_cloned_repo_ref(self) -> str:
        """Get the cloned repository reference.

        Returns:
            The repository reference as a string or empty string if the repository is not cloned.
        """
        cmd = [GIT, "-C", str(self.working_dir), "describe", "--tags", "--exact-match"]
        try:
            ref = subprocess.check_output(cmd).decode()
        except subprocess.CalledProcessError as e:
            logger.debug(e)
            return ""
        return ref.strip()
