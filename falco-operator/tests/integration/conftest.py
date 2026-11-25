# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for charm integration tests."""

import logging
import shutil
import tempfile
import typing
import uuid
from collections.abc import Generator
from pathlib import Path

import jubilant
import pytest

from .helpers import (
    FALCO_APP,
    PRINCIPAL_APP,
    PRINCIPAL_APP_CONSTRAINTS,
    PRINCIPAL_APP_UNITS,
    RULES_FILE_NAME,
    RULES_V2_MARKER,
    Deployment,
    OciRegistry,
    _extract_falcoctl,
    _free_port,
    _gateway,
    _install_ca,
    _write_rules_file,
)

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module", name="charm")
def charm_fixture(charm_paths):
    """Get the falco charm path from built artifacts."""
    return charm_paths["falco"].path


@pytest.fixture(scope="session", name="juju")
def juju_fixture(request: pytest.FixtureRequest) -> Generator[jubilant.Juju, None, None]:
    """Pytest fixture that wraps :meth:`jubilant.with_model`."""

    def show_debug_log(juju: jubilant.Juju):
        """Show debug log.

        Args:
            juju: the Juju object.
        """
        if request.session.testsfailed:
            log = juju.debug_log(limit=1000)
            print(log, end="")

    use_existing = request.config.getoption("--use-existing", default=False)
    if use_existing:
        juju = jubilant.Juju()
        yield juju
        show_debug_log(juju)
        return

    model = request.config.getoption("--model")
    if model:
        juju = jubilant.Juju(model=model)
        juju.wait_timeout = 10 * 60
        yield juju
        show_debug_log(juju)
        return

    keep_models = typing.cast(bool, request.config.getoption("--keep-models"))
    with jubilant.temp_model(keep=keep_models) as juju:
        juju.wait_timeout = 10 * 60
        yield juju
        show_debug_log(juju)
        return


@pytest.fixture(scope="module", name="deployment")
def deployment_fixture(
    juju: jubilant.Juju,
    charm: str,
    pytestconfig: pytest.Config,
) -> Deployment:
    """Deploy the shared test topology used by the integration tests."""
    principal_app = PRINCIPAL_APP
    falco_app = FALCO_APP
    current = juju.status()
    if principal_app not in current.apps:
        logger.info("Deploying %s with constraints: %s", principal_app, PRINCIPAL_APP_CONSTRAINTS)
        juju.deploy(
            "ubuntu",
            app=principal_app,
            num_units=PRINCIPAL_APP_UNITS,
            base=pytestconfig.getoption("--base"),
            constraints=PRINCIPAL_APP_CONSTRAINTS,
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

    status = juju.wait(
        lambda status: jubilant.all_active(status, principal_app, falco_app),
        timeout=juju.wait_timeout,
        error=jubilant.any_error,
    )
    units = status.get_units(falco_app)
    if not units:
        raise RuntimeError(f"No {falco_app} units found after deployment")
    unit_names = list(units)
    return Deployment(
        principal_app=principal_app,
        falco_app=falco_app,
        units=unit_names,
        gateway=_gateway(juju, unit_names[0]),
    )


@pytest.fixture(scope="module", name="registry")
def registry_fixture(
    juju: jubilant.Juju,
    deployment: Deployment,
    charm: str,
) -> Generator[OciRegistry, None, None]:
    """Start an authenticated registry and extract falcoctl for pushing rules."""
    if shutil.which("docker") is None:
        pytest.skip("Docker is required for the OCI registry integration test")
    root = Path(tempfile.mkdtemp(prefix="falco-oci-registry-", dir=Path.home()))
    registry = OciRegistry(
        root=root,
        host=deployment.gateway,
        port=_free_port(),
        falcoctl_binary=_extract_falcoctl(Path(charm), root / "falcoctl"),
    )
    registry.start()
    for unit in deployment.units:
        _install_ca(juju, unit, registry.ca_cert)
    logger.info("Started test OCI registry at %s", registry.address)
    try:
        yield registry
    finally:
        registry.stop()


@pytest.fixture(scope="module", name="correct_secret")
def correct_secret_fixture(
    juju: jubilant.Juju,
    deployment: Deployment,
    registry: OciRegistry,
):
    """Create and configure a secret with valid registry credentials."""
    secret = juju.add_secret(
        f"falco-oci-rules-correct-{uuid.uuid4().hex[:8]}",
        {
            "username": registry.username,
            "password": registry.password,
            "oci-ref": registry.oci_ref,
        },
        info="OCI rules integration test - correct credentials",
    )
    juju.grant_secret(secret, deployment.falco_app)
    juju.config(
        deployment.falco_app,
        {"custom-rules-secret": str(secret), "custom-rules-refresh-interval": "5m"},
    )
    return secret


@pytest.fixture(scope="module", name="v2_rules")
def v2_rules_fixture(registry: OciRegistry) -> Path:
    """Push the updated rules artifact."""
    rules = registry.root / "v2" / RULES_FILE_NAME
    _write_rules_file(rules, RULES_V2_MARKER)
    registry.push_rules(rules, "1.0.1")
    return rules
