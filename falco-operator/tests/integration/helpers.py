# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Shared helpers for the Falco integration tests."""

from __future__ import annotations

import base64
import dataclasses
import json
import logging
import os
import re
import shlex
import shutil
import socket
import ssl
import subprocess
import time
import urllib.error
import urllib.request
import uuid
import zipfile
from pathlib import Path

import jubilant
import pytest

logger = logging.getLogger(__name__)

FALCO_APP = "falco"
PRINCIPAL_APP = "ubuntu"
PRINCIPAL_APP_UNITS = 2
PRINCIPAL_APP_CONSTRAINTS = {"virt-type": "virtual-machine"}


@dataclasses.dataclass(frozen=True)
class Deployment:
    """A deployed principal and its Falco subordinate units."""

    juju: jubilant.Juju
    principal_app: str
    falco_app: str
    units: list[str]
    gateway: str = ""

    @property
    def unit(self) -> str:
        """Return the first deployed Falco unit."""
        return self.units[0]


def deploy_falco(
    juju: jubilant.Juju,
    charm: str,
    pytestconfig: pytest.Config,
    *,
    principal_app: str,
    falco_app: str,
    num_units: int,
    constraints: dict[str, str],
    gateway: bool = False,
) -> Deployment:
    """Deploy a principal charm with the Falco subordinate and wait for both."""
    current = juju.status()
    if principal_app not in current.apps:
        logger.info("Deploying %s with constraints: %s", principal_app, constraints)
        juju.deploy(
            "ubuntu",
            app=principal_app,
            num_units=num_units,
            base=pytestconfig.getoption("--base"),
            constraints=constraints,
        )

    if falco_app not in current.apps:
        logger.info("Deploying %s", falco_app)
        juju.deploy(charm, app=falco_app)

    logger.info("Integrating %s with %s", principal_app, falco_app)
    try:
        juju.integrate(principal_app, falco_app)
    except jubilant.CLIError as exc:
        if "already" not in str(exc).lower():
            raise

    logger.info("Waiting for deployment to settle")
    status = juju.wait(
        lambda status: jubilant.all_active(status, principal_app, falco_app),
        timeout=juju.wait_timeout,
        error=jubilant.any_error,
    )
    units = status.get_units(falco_app)
    if not units:
        raise RuntimeError(f"No {falco_app} units found after deployment")
    unit_names = list(units)
    gateway_address = _gateway(juju, unit_names[0]) if gateway else ""
    return Deployment(
        juju=juju,
        principal_app=principal_app,
        falco_app=falco_app,
        units=unit_names,
        gateway=gateway_address,
    )


def _gateway(juju: jubilant.Juju, unit: str) -> str:
    """Return the unit's default gateway, which is reachable from the test runner."""
    gateway = juju.ssh(unit, "ip -4 route show default | awk '{print $3; exit}'").strip()
    if not gateway:
        raise RuntimeError(f"Could not determine the default gateway for {unit}")
    return gateway


REGISTRY_USERNAME = "falco-test"
REGISTRY_PASSWORD = "falco-test-password"  # nosec B105 - local test credential
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
        self.ca_cert = root / "ca.crt"
        self._container_name = f"falco-oci-test-{uuid.uuid4().hex[:8]}"
        self._auth_dir = root / "auth"
        self._certs_dir = root / "certs"

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
        config = self.root / "falcoctl-push.yaml"
        config.write_text(
            "registry:\n"
            "  auth:\n"
            "    basic:\n"
            f"      - registry: {json.dumps(self.address)}\n"
            f"        user: {json.dumps(self.username)}\n"
            f"        password: {json.dumps(self.password)}\n",
            encoding="utf-8",
        )
        env = {**os.environ, "SSL_CERT_FILE": str(self.ca_cert)}
        command = [
            str(self.falcoctl_binary),
            "--config",
            str(config),
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
        """Create a test CA and a registry certificate trusted by the units."""
        self._certs_dir.mkdir(parents=True)
        ca_key = self.root / "ca.key"
        server_key = self._certs_dir / "server.key"
        server_csr = self.root / "server.csr"
        server_cert = self._certs_dir / "server.crt"
        server_ext = self.root / "server.ext"

        _run_command(
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            str(ca_key),
            "-out",
            str(self.ca_cert),
            "-days",
            "1",
            "-subj",
            "/CN=falco-oci-test-ca",
            "-addext",
            "basicConstraints=critical,CA:TRUE",
        )
        _run_command(
            "openssl",
            "req",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            str(server_key),
            "-out",
            str(server_csr),
            "-subj",
            f"/CN={self.host}",
        )
        server_ext.write_text(
            f"subjectAltName=IP:{self.host},DNS:localhost\n",
            encoding="utf-8",
        )
        _run_command(
            "openssl",
            "x509",
            "-req",
            "-in",
            str(server_csr),
            "-CA",
            str(self.ca_cert),
            "-CAkey",
            str(ca_key),
            "-CAcreateserial",
            "-out",
            str(server_cert),
            "-days",
            "1",
            "-extfile",
            str(server_ext),
        )

    def _write_htpasswd(self) -> None:
        """Write the registry htpasswd file using the httpd helper image."""
        self._auth_dir.mkdir()
        result = self._docker(
            "run",
            "--rm",
            "--entrypoint",
            "htpasswd",
            "httpd:2",
            "-nbB",
            self.username,
            self.password,
        )
        (self._auth_dir / "htpasswd").write_text(result.stdout, encoding="utf-8")

    def _wait_until_ready(self) -> None:
        """Wait for the registry to accept authenticated TLS requests."""
        context = ssl.create_default_context(cafile=str(self.ca_cert))
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            try:
                if self._v2_status(context, self.username, self.password) == 200:
                    break
            except (OSError, urllib.error.URLError):
                pass
            time.sleep(1)
        else:
            logs = self._docker("logs", self._container_name, check=False)
            raise RuntimeError(
                f"Registry at {self.address} did not become ready:\n{logs.stdout}\n{logs.stderr}"
            )

        if self._v2_status(context, self.username, "wrong-password") != 401:
            raise RuntimeError("Registry did not reject an incorrect password")

    def _v2_status(self, context: ssl.SSLContext, username: str, password: str) -> int:
        """Return the HTTP status for the registry API root with basic auth."""
        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
        request = urllib.request.Request(
            f"https://{self.address}/v2/",
            headers={"Authorization": f"Basic {credentials}"},
        )
        try:
            with urllib.request.urlopen(request, context=context, timeout=5) as response:
                return response.status
        except urllib.error.HTTPError as exc:
            return exc.code


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
    encoded = base64.b64encode(ca_cert.read_bytes()).decode()
    juju.ssh(
        unit,
        (
            f"printf '%s' '{encoded}' | base64 -d | "
            "sudo -n tee /usr/local/share/ca-certificates/falco-oci-test.crt >/dev/null && "
            "sudo -n update-ca-certificates"
        ),
    )


def _rules_dir(juju: jubilant.Juju, unit: str) -> str:
    """Return the managed Falco rules directory from the follower unit file."""
    try:
        service = juju.ssh(unit, "sudo -n systemctl cat falcoctl-rules-follow")
    except jubilant.CLIError:
        service = ""
    match = re.search(r"--rulesfiles-dir\s+(\S+)", service)
    if match:
        return match.group(1)

    result = juju.ssh(
        unit,
        (
            "sudo -n find /var/lib/juju/agents "
            "-path '*/charm/falco/etc/falco/rules.d' -type d -print -quit"
        ),
    ).strip()
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
    result = juju.ssh(
        unit,
        (
            f"sudo -n find {shlex.quote(rules_dir)} -maxdepth 1 -type f "
            "\\( -name '*.yaml' -o -name '*.yml' \\) -print"
        ),
    )
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
            content = juju.ssh(unit, f"sudo -n cat {shlex.quote(str(rule_file))}")
        except jubilant.CLIError as exc:
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
