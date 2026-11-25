# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Shared deployment helpers for integration tests."""

from __future__ import annotations

import dataclasses
import logging

import jubilant
import pytest

logger = logging.getLogger(__name__)

FALCO_APP = "falco"
PRINCIPAL_APP = "ubuntu"
PRINCIPAL_APP_UNITS = 2
PRINCIPAL_APP_CONSTRAINTS = {"virt-type": "virtual-machine"}

OCI_FALCO_APP = "falco-oci"
OCI_PRINCIPAL_APP = "ubuntu-oci"
OCI_PRINCIPAL_APP_UNITS = 1
OCI_PRINCIPAL_APP_CONSTRAINTS = {"virt-type": "virtual-machine"}


@dataclasses.dataclass(frozen=True)
class Deployment:
    """A deployed principal and its Falco subordinate units."""

    juju: jubilant.Juju
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
    logger.info("Deploying %s with constraints: %s", principal_app, constraints)
    juju.deploy(
        "ubuntu",
        app=principal_app,
        num_units=num_units,
        base=pytestconfig.getoption("--base"),
        constraints=constraints,
    )

    logger.info("Deploying %s", falco_app)
    juju.deploy(charm, app=falco_app)

    logger.info("Integrating %s with %s", principal_app, falco_app)
    juju.integrate(principal_app, falco_app)

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
    return Deployment(juju=juju, units=unit_names, gateway=gateway_address)


def _gateway(juju: jubilant.Juju, unit: str) -> str:
    """Return the unit's default gateway, which is reachable from the test runner."""
    gateway = juju.ssh(unit, "ip -4 route show default | awk '{print $3; exit}'").strip()
    if not gateway:
        raise RuntimeError(f"Could not determine the default gateway for {unit}")
    return gateway
