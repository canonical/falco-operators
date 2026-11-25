# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for charm integration tests."""

import logging
import shutil
import tempfile
import typing
from collections.abc import Generator
from pathlib import Path

import jubilant
import pytest

from tests.integration.oci_registry import (
    FALCO_APP,
    PRINCIPAL_APP,
    PRINCIPAL_APP_CONSTRAINTS,
    PRINCIPAL_APP_UNITS,
    Deployment,
    OciRegistry,
    _extract_falcoctl,
    _free_port,
    _gateway,
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
def registry_fixture(deployment: Deployment, charm: str) -> Generator[OciRegistry, None, None]:
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
    logger.info("Started test OCI registry at %s", registry.address)
    try:
        yield registry
    finally:
        registry.stop()
