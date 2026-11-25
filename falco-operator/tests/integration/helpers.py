# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Shared helpers for the Falco integration tests."""

from __future__ import annotations

import dataclasses
import json
import logging
import os
import re
import shlex
import shutil
import socket
import subprocess
import time
import uuid
import zipfile
from pathlib import Path

import jubilant
import requests

logger = logging.getLogger(__name__)

FALCO_APP = "falco"
PRINCIPAL_APP = "ubuntu"
PRINCIPAL_APP_UNITS = 2
PRINCIPAL_APP_CONSTRAINTS = {"virt-type": "virtual-machine"}


@dataclasses.dataclass(frozen=True)
class Deployment:
    """A deployed principal and its Falco subordinate units."""

    principal_app: str
    falco_app: str
    units: list[str]
    gateway: str = ""

    @property
    def unit(self) -> str:
        """Return the first deployed Falco unit."""
        return self.units[0]


def _gateway(juju: jubilant.Juju, unit: str) -> str:
    """Return the unit's default gateway, which is reachable from the test runner."""
    gateway = juju.exec(
        "ip -4 route show default | awk '{print $3; exit}'", unit=unit
    ).stdout.strip()
    if not gateway:
        raise RuntimeError(f"Could not determine the default gateway for {unit}")
    return gateway


REGISTRY_USERNAME = "falco-test"
REGISTRY_PASSWORD = "falco-test-password"  # nosec B105 - local test credential
REGISTRY_HTPASSWD = "falco-test:$2y$05$03/yOI6axBGYTFcN1r5.L.ddKEZk7gu/0bRtkqTm/cxTJ5I1aeFzS\n"
REGISTRY_REPO = "falco-rules"
REGISTRY_TAG = "latest"
RULES_FILE_NAME = "oci-test-rules.yaml"
RULES_REFRESH_INTERVAL = "5m"
# The follower checks the registry every five minutes. Give it one full interval plus
# a generous margin to download and install the updated artifact.
RULE_UPDATE_TIMEOUT = 8 * 60

RULES_V1_MARKER = "OCI registry test rule v1"
RULES_V2_MARKER = "OCI registry test rule v2"


class OciRegistry:
    """A temporary TLS-enabled OCI registry with htpasswd authentication."""

    def __init__(
        self,
        root: Path,
        host: str,
        port: int,
        falcoctl_binary: Path,
    ) -> None:
        """Initialize the registry.

        Args:
            root: Directory for certificates, authentication, and push tooling.
            host: Hostname or IP address the units use to reach the registry.
            port: Port the registry listens on.
            falcoctl_binary: Path to the falcoctl binary used to push artifacts.
        """
        self.root = root
        self.host = host
        self.port = port
        self.falcoctl_binary = falcoctl_binary
        self.username = REGISTRY_USERNAME
        self.password = REGISTRY_PASSWORD
        self.ca_cert = root / "certs" / "server.crt"
        self._container_name = f"falco-oci-test-{uuid.uuid4().hex[:8]}"
        self._auth_dir = root / "auth"
        self._certs_dir = root / "certs"
        self._falcoctl_config = root / "falcoctl.yaml"

    @property
    def address(self) -> str:
        """Return the registry address used in OCI references."""
        return f"{self.host}:{self.port}"

    @property
    def oci_ref(self) -> str:
        """Return the artifact reference configured in the charm secret."""
        return f"{self.address}/{REGISTRY_REPO}:{REGISTRY_TAG}"

    def start(self) -> None:
        """Create the registry configuration and start the Docker registry."""
        self._create_certificates()
        self._write_htpasswd()
        self._write_falcoctl_config()
        self._docker(
            "run",
            "-d",
            "--name",
            self._container_name,
            "-p",
            f"{self.host}:{self.port}:5000",
            "-v",
            f"{self._auth_dir}:/auth",
            "-v",
            f"{self._certs_dir}:/certs",
            "-e",
            "REGISTRY_HTTP_ADDR=0.0.0.0:5000",
            "-e",
            "REGISTRY_HTTP_TLS_CERTIFICATE=/certs/server.crt",
            "-e",
            "REGISTRY_HTTP_TLS_KEY=/certs/server.key",
            "-e",
            "REGISTRY_AUTH=htpasswd",
            "-e",
            "REGISTRY_AUTH_HTPASSWD_REALM=Registry",
            "-e",
            "REGISTRY_AUTH_HTPASSWD_PATH=/auth/htpasswd",
            "registry:2",
        )
        self._wait_until_ready()

    def stop(self) -> None:
        """Stop the registry and remove its temporary files."""
        self._docker("rm", "-f", self._container_name, check=False)
        shutil.rmtree(self.root, ignore_errors=True)

    def push_rules(self, rules_file: Path, version: str) -> None:
        """Push a Falco rulesfile artifact to the registry.

        Args:
            rules_file: YAML file containing the rules to push.
            version: Semver-compatible artifact version.
        """
        env = {**os.environ, "SSL_CERT_FILE": str(self.ca_cert)}
        command = [
            str(self.falcoctl_binary),
            "--config",
            str(self._falcoctl_config),
            "--log-format",
            "text",
            "registry",
            "push",
            "--type",
            "rulesfile",
            "--version",
            version,
            self.oci_ref,
            str(rules_file),
        ]
        result = subprocess.run(command, capture_output=True, text=True, env=env, check=False)
        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to push rules to {self.oci_ref}:\n{result.stdout}\n{result.stderr}"
            )
        logger.info("Pushed %s as %s", rules_file, self.oci_ref)

    def _docker(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        """Run a Docker command as the test runner user."""
        return subprocess.run(
            ["docker", *args],
            capture_output=True,
            text=True,
            check=check,
        )

    def _create_certificates(self) -> None:
        """Create one self-signed certificate used by the registry and units."""
        self._certs_dir.mkdir(parents=True)
        server_key = self._certs_dir / "server.key"
        server_cert = self._certs_dir / "server.crt"
        self.ca_cert = server_cert

        _run_command(
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            str(server_key),
            "-out",
            str(server_cert),
            "-days",
            "1",
            "-subj",
            f"/CN={self.host}",
            "-addext",
            f"subjectAltName=IP:{self.host},DNS:localhost",
            "-addext",
            "basicConstraints=critical,CA:TRUE",
        )

    def _write_htpasswd(self) -> None:
        """Write the fixed test htpasswd file."""
        self._auth_dir.mkdir()
        (self._auth_dir / "htpasswd").write_text(REGISTRY_HTPASSWD, encoding="utf-8")

    def _write_falcoctl_config(self) -> None:
        """Write the falcoctl credentials used to push artifacts."""
        self._falcoctl_config.write_text(
            "registry:\n"
            "  auth:\n"
            "    basic:\n"
            f"      - registry: {json.dumps(self.address)}\n"
            f"        user: {json.dumps(self.username)}\n"
            f"        password: {json.dumps(self.password)}\n",
            encoding="utf-8",
        )

    def _wait_until_ready(self) -> None:
        """Wait for the registry to accept authenticated TLS requests."""
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            try:
                response = requests.get(
                    f"https://{self.address}/v2/",
                    auth=(self.username, self.password),
                    verify=str(self.ca_cert),
                    timeout=5,
                )
                if response.status_code == 200:
                    break
            except requests.RequestException:
                pass
            time.sleep(1)
        else:
            logs = self._docker("logs", self._container_name, check=False)
            raise RuntimeError(
                f"Registry at {self.address} did not become ready:\n{logs.stdout}\n{logs.stderr}"
            )

        response = requests.get(
            f"https://{self.address}/v2/",
            auth=(self.username, "wrong-password"),
            verify=str(self.ca_cert),
            timeout=5,
        )
        if response.status_code != 401:
            raise RuntimeError("Registry did not reject an incorrect password")


def _run_command(*command: str) -> None:
    """Run a command and raise a useful error if it fails."""
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {shlex.join(command)}\n{result.stderr}")


def _extract_falcoctl(charm_path: Path, destination: Path) -> Path:
    """Extract falcoctl from the built charm so the host can push artifacts."""
    if charm_path.is_dir():
        source = charm_path / "falco" / "usr" / "bin" / "falcoctl"
        if not source.is_file():
            source = charm_path / "usr" / "bin" / "falcoctl"
        if not source.is_file():
            raise RuntimeError(f"falcoctl not found in {charm_path}")
        shutil.copy2(source, destination)
    else:
        with zipfile.ZipFile(charm_path) as archive:
            names = [name for name in archive.namelist() if name.endswith("usr/bin/falcoctl")]
            if not names:
                raise RuntimeError(f"falcoctl not found in {charm_path}")
            destination.write_bytes(archive.read(names[0]))
    destination.chmod(0o755)
    return destination


def _free_port() -> int:
    """Return an available local TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("", 0))
        return int(sock.getsockname()[1])


def _install_ca(juju: jubilant.Juju, unit: str, ca_cert: Path) -> None:
    """Install the test CA in the unit's system trust store."""
    remote = f"/tmp/{uuid.uuid4().hex}-falco-oci-test-ca.crt"
    juju.scp(ca_cert, f"{unit}:{remote}")
    juju.exec(
        f"install -m 0644 {remote} /usr/local/share/ca-certificates/falco-oci-test-ca.crt",
        unit=unit,
    )
    juju.exec("update-ca-certificates", unit=unit)


def _rules_dir(juju: jubilant.Juju, unit: str) -> str:
    """Return the managed Falco rules directory from the follower unit file."""
    try:
        service = juju.exec("systemctl cat falcoctl-rules-follow", unit=unit).stdout
    except jubilant.TaskError:
        service = ""
    match = re.search(r"--rulesfiles-dir\s+(\S+)", service)
    if match:
        return match.group(1)

    result = juju.exec(
        "find /var/lib/juju/agents -path '*/charm/falco/etc/falco/rules.d' -type d -print -quit",
        unit=unit,
    ).stdout.strip()
    if not result:
        raise RuntimeError(f"Could not find the managed rules directory on {unit}")
    return result


def _write_rules_file(path: Path, marker: str) -> None:
    """Write a minimal valid Falco rules file containing *marker* in its output."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "- rule: OCI Test Rule\n"
        "  desc: Rule installed by the Falco operator integration test\n"
        "  condition: evt.type = execve\n"
        f"  output: {marker}\n"
        "  priority: WARNING\n"
        "  tags: [oci, integration]\n",
        encoding="utf-8",
    )


def _installed_rule_files(juju: jubilant.Juju, unit: str, rules_dir: str) -> list[str]:
    """Return the YAML rule files in the managed rules directory."""
    result = juju.exec(
        (
            f"find {shlex.quote(rules_dir)} -maxdepth 1 -type f "
            "\\( -name '*.yaml' -o -name '*.yml' \\) -print"
        ),
        unit=unit,
    ).stdout
    return [line for line in result.splitlines() if line.strip()]


def _wait_for_rule(
    juju: jubilant.Juju,
    unit: str,
    rules_dir: str,
    marker: str,
    timeout: float,
) -> str:
    """Wait until the managed rule file contains *marker* and return its contents."""
    rule_file = Path(rules_dir) / RULES_FILE_NAME
    deadline = time.monotonic() + timeout
    last_content = ""
    while time.monotonic() < deadline:
        try:
            content = juju.exec(f"cat {shlex.quote(str(rule_file))}", unit=unit).stdout
        except jubilant.TaskError as exc:
            last_content = str(exc)
        else:
            if marker in content:
                return content
            last_content = content
        time.sleep(10)

    raise AssertionError(
        f"Rule marker {marker!r} was not installed in {rule_file} on {unit} "
        f"within {timeout} seconds. Last content:\n{last_content}"
    )
