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

from .deployment import (
    FALCO_APP,
    OCI_FALCO_APP,
    OCI_PRINCIPAL_APP,
    OCI_PRINCIPAL_APP_CONSTRAINTS,
    OCI_PRINCIPAL_APP_UNITS,
    PRINCIPAL_APP,
    PRINCIPAL_APP_CONSTRAINTS,
    PRINCIPAL_APP_UNITS,
    Deployment,
    deploy_falco,
)
from .oci_registry import OciRegistry, _extract_falcoctl, _free_port

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
    """Deploy the standard test topology used by the charm integration tests."""
    return deploy_falco(
        juju,
        charm,
        pytestconfig,
        principal_app=PRINCIPAL_APP,
        falco_app=FALCO_APP,
        num_units=PRINCIPAL_APP_UNITS,
        constraints=PRINCIPAL_APP_CONSTRAINTS,
    )


@pytest.fixture(scope="module", name="oci_deployment")
def oci_deployment_fixture(
    juju: jubilant.Juju,
    charm: str,
    pytestconfig: pytest.Config,
) -> Deployment:
    """Deploy a single-unit topology for the OCI rules integration test."""
    return deploy_falco(
        juju,
        charm,
        pytestconfig,
        principal_app=OCI_PRINCIPAL_APP,
        falco_app=OCI_FALCO_APP,
        num_units=OCI_PRINCIPAL_APP_UNITS,
        constraints=OCI_PRINCIPAL_APP_CONSTRAINTS,
        gateway=True,
    )


@pytest.fixture(scope="module", name="registry")
def registry_fixture(oci_deployment: Deployment, charm: str) -> Generator[OciRegistry, None, None]:
    """Start an authenticated registry and extract falcoctl for pushing rules."""
    if shutil.which("docker") is None:
        pytest.skip("Docker is required for the OCI registry integration test")
    root = Path(tempfile.mkdtemp(prefix="falco-oci-registry-", dir=Path.home()))
    registry = OciRegistry(
        root=root,
        host=oci_deployment.gateway,
        port=_free_port(),
        falcoctl_binary=_extract_falcoctl(Path(charm), root / "falcoctl"),
    )
    registry.start()
    logger.info("Started test OCI registry at %s", registry.address)
    try:
        yield registry
    finally:
        registry.stop()
