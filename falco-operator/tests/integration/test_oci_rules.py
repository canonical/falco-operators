#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for fetching Falco rules from an authenticated OCI registry."""

from __future__ import annotations

import base64
import dataclasses
import io
import json
import logging
import os
import platform
import re
import shlex
import shutil
import socket
import ssl
import subprocess
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
import uuid
import warnings
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

import jubilant
import pytest

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)

FALCO_APP = "falco-oci"
PRINCIPAL_APP = "ubuntu-oci"
PRINCIPAL_APP_UNITS = 1
PRINCIPAL_APP_CONSTRAINTS = {"virt-type": "virtual-machine"}

REGISTRY_USERNAME = "falco-test"
REGISTRY_PASSWORD = "falco-test-password"  # nosec B105 - local test credential
REGISTRY_REPO = "falco-rules"
REGISTRY_TAG = "latest"
RULES_FILE_NAME = "oci-test-rules.yaml"
RULES_REFRESH_INTERVAL = "5m"
# The follower checks the registry every five minutes. Give it one full interval plus
# a generous margin to download and install the updated artifact.
RULE_UPDATE_TIMEOUT = 8 * 60

REGISTRY_VERSION = "3.1.2"
REGISTRY_RELEASE_URL = (
    "https://github.com/distribution/distribution/releases/download/"
    f"v{REGISTRY_VERSION}/registry_{REGISTRY_VERSION}_linux_{{arch}}.tar.gz"
)

RULES_V1_MARKER = "OCI registry test rule v1"
RULES_V2_MARKER = "OCI registry test rule v2"


@dataclasses.dataclass(frozen=True)
class Deployment:
    """The deployed Falco application and its registry-visible network details."""

    juju: jubilant.Juju
    unit: str
    gateway: str


class OciRegistry:
    """A temporary TLS-enabled OCI registry with htpasswd authentication."""

    def __init__(
        self,
        root: Path,
        host: str,
        port: int,
        registry_binary: Path,
        falcoctl_binary: Path,
    ) -> None:
        """Initialize the registry.

        Args:
            root: Directory for certificates, configuration, and registry data.
            host: Hostname or IP address the units use to reach the registry.
            port: Port the registry listens on.
            registry_binary: Path to the distribution registry binary.
            falcoctl_binary: Path to the falcoctl binary used to push artifacts.
        """
        self.root = root
        self.host = host
        self.port = port
        self.registry_binary = registry_binary
        self.falcoctl_binary = falcoctl_binary
        self.username = REGISTRY_USERNAME
        self.password = REGISTRY_PASSWORD
        self.ca_cert = root / "ca.crt"
        self._config = root / "registry.yaml"
        self._data = root / "data"
        self._log = root / "registry.log"
        self._process: subprocess.Popen[bytes] | None = None

    @property
    def address(self) -> str:
        """Return the registry address used in OCI references."""
        return f"{self.host}:{self.port}"

    @property
    def oci_ref(self) -> str:
        """Return the artifact reference configured in the charm secret."""
        return f"{self.address}/{REGISTRY_REPO}:{REGISTRY_TAG}"

    def start(self) -> None:
        """Create the registry configuration and start the registry process."""
        self._create_certificates()
        self._write_config()
        with self._log.open("w", encoding="utf-8") as log_file:
            self._process = subprocess.Popen(
                [str(self.registry_binary), "serve", str(self._config)],
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        self._wait_until_ready()

    def stop(self) -> None:
        """Stop the registry and remove its temporary files."""
        if self._process is not None and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()
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

    def _create_certificates(self) -> None:
        """Create a test CA and a registry certificate trusted by the units."""
        ca_key = self.root / "ca.key"
        server_key = self.root / "server.key"
        server_csr = self.root / "server.csr"
        server_cert = self.root / "server.crt"
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

    def _write_config(self) -> None:
        """Write the registry configuration and htpasswd file."""
        self._data.mkdir(parents=True)
        htpasswd = self.root / "htpasswd"
        htpasswd.write_text(
            f"{self.username}:{_bcrypt_hash(self.password)}\n",
            encoding="utf-8",
        )
        self._config.write_text(
            "version: 0.1\n"
            "log:\n"
            "  level: info\n"
            "storage:\n"
            "  filesystem:\n"
            f"    rootdirectory: {json.dumps(str(self._data))}\n"
            "http:\n"
            f"  addr: 0.0.0.0:{self.port}\n"
            "  tls:\n"
            f"    certificate: {json.dumps(str(self.root / 'server.crt'))}\n"
            f"    key: {json.dumps(str(self.root / 'server.key'))}\n"
            "auth:\n"
            "  htpasswd:\n"
            "    realm: falco-oci-test\n"
            f"    path: {json.dumps(str(htpasswd))}\n",
            encoding="utf-8",
        )

    def _wait_until_ready(self) -> None:
        """Wait for the registry to accept authenticated TLS requests."""
        context = ssl.create_default_context(cafile=str(self.ca_cert))
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            if self._process is not None and self._process.poll() is not None:
                raise RuntimeError(
                    f"Registry exited with code {self._process.returncode}:\n"
                    f"{self._log.read_text(encoding='utf-8')}"
                )
            try:
                if self._v2_status(context, self.username, self.password) == 200:
                    break
            except (OSError, urllib.error.URLError):
                pass
            time.sleep(1)
        else:
            raise RuntimeError(
                f"Registry at {self.address} did not become ready:\n"
                f"{self._log.read_text(encoding='utf-8')}"
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


def _bcrypt_hash(password: str) -> str:
    """Return a bcrypt hash accepted by the registry's htpasswd authentication."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        try:
            import crypt
        except ImportError:
            crypt = None  # type: ignore[assignment]
        if crypt is not None:
            hashed = crypt.crypt(password, crypt.mksalt(crypt.METHOD_BLOWFISH))
            if hashed:
                return hashed

    htpasswd = shutil.which("htpasswd")
    if htpasswd is None:
        raise RuntimeError(
            "Cannot generate a bcrypt hash. Use Python 3.12 or install apache2-utils."
        )
    result = subprocess.run(
        [htpasswd, "-nbB", "user", password],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to generate htpasswd entry:\n{result.stderr}")
    return result.stdout.strip().split(":", maxsplit=1)[1]


def _run_command(*command: str) -> None:
    """Run a command and raise a useful error if it fails."""
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {shlex.join(command)}\n{result.stderr}")


def _ensure_registry_binary() -> Path:
    """Return a cached distribution registry binary, downloading it if needed."""
    machine = platform.machine().lower()
    arch = {
        "x86_64": "amd64",
        "amd64": "amd64",
        "aarch64": "arm64",
        "arm64": "arm64",
    }.get(machine)
    if arch is None:
        raise RuntimeError(f"Unsupported architecture for the OCI test registry: {machine}")

    cache = Path.home() / ".cache" / "falco-operators" / f"registry-{REGISTRY_VERSION}"
    if cache.is_file() and os.access(cache, os.X_OK):
        return cache

    cache.parent.mkdir(parents=True, exist_ok=True)
    url = REGISTRY_RELEASE_URL.format(arch=arch)
    logger.info("Downloading OCI registry from %s", url)
    with urllib.request.urlopen(url, timeout=120) as response:
        archive = response.read()

    extract_dir = cache.parent / f"registry-{REGISTRY_VERSION}-extract"
    shutil.rmtree(extract_dir, ignore_errors=True)
    extract_dir.mkdir()
    try:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
            tar.extractall(extract_dir, filter="data")
        extracted = extract_dir / "registry"
        if not extracted.is_file():
            raise RuntimeError(f"Registry archive did not contain a registry binary: {url}")
        shutil.move(str(extracted), cache)
    finally:
        shutil.rmtree(extract_dir, ignore_errors=True)

    cache.chmod(0o755)
    return cache


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


def _gateway(juju: jubilant.Juju, unit: str) -> str:
    """Return the unit's default gateway, which is reachable from the test runner."""
    gateway = juju.ssh(unit, "ip -4 route show default | awk '{print $3; exit}'").strip()
    if not gateway:
        raise RuntimeError(f"Could not determine the default gateway for {unit}")
    return gateway


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


@pytest.fixture(scope="module", name="deployment")
def deployment_fixture(
    juju: jubilant.Juju,
    charm: str,
    pytestconfig: pytest.Config,
) -> Deployment:
    """Deploy a principal machine and the Falco subordinate charm."""
    logger.info("Deploying %s", PRINCIPAL_APP)
    juju.deploy(
        "ubuntu",
        app=PRINCIPAL_APP,
        num_units=PRINCIPAL_APP_UNITS,
        base=pytestconfig.getoption("--base"),
        constraints=PRINCIPAL_APP_CONSTRAINTS,
    )

    logger.info("Deploying %s", FALCO_APP)
    juju.deploy(charm, app=FALCO_APP)

    logger.info("Integrating %s with %s", PRINCIPAL_APP, FALCO_APP)
    juju.integrate(PRINCIPAL_APP, FALCO_APP)

    status = juju.wait(
        lambda status: jubilant.all_active(status, PRINCIPAL_APP, FALCO_APP),
        timeout=juju.wait_timeout,
        error=jubilant.any_error,
    )
    units = status.get_units(FALCO_APP)
    if not units:
        raise RuntimeError("No Falco units found after deployment")
    unit = next(iter(units))
    return Deployment(juju=juju, unit=unit, gateway=_gateway(juju, unit))


@pytest.fixture(scope="module", name="registry")
def registry_fixture(deployment: Deployment, charm: str) -> Iterator[OciRegistry]:
    """Start an authenticated registry and extract falcoctl for pushing rules."""
    root = Path(tempfile.mkdtemp(prefix="falco-oci-registry-", dir=Path.home()))
    registry = OciRegistry(
        root=root,
        host=deployment.gateway,
        port=_free_port(),
        registry_binary=_ensure_registry_binary(),
        falcoctl_binary=_extract_falcoctl(Path(charm), root / "falcoctl"),
    )
    registry.start()
    logger.info("Started test OCI registry at %s", registry.address)
    try:
        yield registry
    finally:
        registry.stop()


def test_oci_rules_with_authenticated_registry(
    deployment: Deployment,
    registry: OciRegistry,
) -> None:
    """
    Arrange: Deploy Falco, start an authenticated TLS OCI registry, and push rules.
    Act: Configure the charm with bad credentials, then with valid credentials, then
        publish an updated rules artifact without changing charm configuration.
    Assert: Bad credentials block the unit, valid credentials install the rules, and
        the follower installs the updated rules automatically.
    """
    juju = deployment.juju
    unit = deployment.unit

    _install_ca(juju, unit, registry.ca_cert)
    rules_dir = _rules_dir(juju, unit)

    suffix = uuid.uuid4().hex[:8]
    rules_v1 = registry.root / "v1" / RULES_FILE_NAME
    _write_rules_file(rules_v1, RULES_V1_MARKER)
    registry.push_rules(rules_v1, "1.0.0")

    logger.info("Configuring the charm with an incorrect registry password")
    wrong_secret = juju.add_secret(
        f"falco-oci-rules-wrong-{suffix}",
        {
            "username": registry.username,
            "password": "incorrect-password",
            "oci-ref": registry.oci_ref,
        },
        info="OCI rules integration test - incorrect credentials",
    )
    juju.grant_secret(wrong_secret, FALCO_APP)
    juju.config(
        FALCO_APP,
        {
            "custom-rules-secret": str(wrong_secret),
            "custom-rules-refresh-interval": RULES_REFRESH_INTERVAL,
        },
    )

    status = juju.wait(
        lambda status: jubilant.all_blocked(status, FALCO_APP),
        timeout=juju.wait_timeout,
        error=jubilant.any_error,
    )
    blocked_units = status.get_units(FALCO_APP)
    assert blocked_units, "No Falco units found after configuring the wrong secret"
    for blocked_unit in blocked_units.values():
        assert blocked_unit.workload_status.message == "Failed to fetch OCI rules"
    assert not _installed_rule_files(juju, unit, rules_dir), (
        "Rules were installed despite the registry rejecting the credentials"
    )

    logger.info("Rotating the charm secret to the correct registry password")
    correct_secret = juju.add_secret(
        f"falco-oci-rules-correct-{suffix}",
        {
            "username": registry.username,
            "password": registry.password,
            "oci-ref": registry.oci_ref,
        },
        info="OCI rules integration test - correct credentials",
    )
    juju.grant_secret(correct_secret, FALCO_APP)
    juju.config(FALCO_APP, {"custom-rules-secret": str(correct_secret)})

    juju.wait(
        lambda status: jubilant.all_active(status, PRINCIPAL_APP, FALCO_APP),
        timeout=juju.wait_timeout,
        error=jubilant.any_error,
    )
    v1_content = _wait_for_rule(juju, unit, rules_dir, RULES_V1_MARKER, timeout=juju.wait_timeout)
    assert RULES_V1_MARKER in v1_content
    assert juju.ssh(unit, "systemctl is-active falcoctl-rules-follow").strip() == "active"

    logger.info("Publishing an updated rules artifact; charm configuration is unchanged")
    rules_v2 = registry.root / "v2" / RULES_FILE_NAME
    _write_rules_file(rules_v2, RULES_V2_MARKER)
    registry.push_rules(rules_v2, "1.0.1")

    v2_content = _wait_for_rule(
        juju, unit, rules_dir, RULES_V2_MARKER, timeout=RULE_UPDATE_TIMEOUT
    )
    assert RULES_V1_MARKER not in v2_content
    assert juju.ssh(unit, "systemctl is-active falcoctl-rules-follow").strip() == "active"
