#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests."""

import logging

import jubilant
import pytest

logger = logging.getLogger(__name__)

FALCO_APP = "falco"
PRINCIPAL_APP = "ubuntu"
PRINCIPAL_APP_UNITS = 2
PRINCIAPL_APP_CONSTRAINTS = {"virt-type": "virtual-machine"}


def test_deploy_charms(juju: jubilant.Juju, charm: str, pytestconfig: pytest.Config):
    """
    Arrange: Deploy a principal charm with VM constraints and falco charm.
    Act: Integrate falco charm with the principal charm.
    Assert: Both applications are deployed and active.
    """
    logger.info("Deploying %s with constraints: %s", PRINCIPAL_APP, PRINCIAPL_APP_CONSTRAINTS)
    juju.deploy(
        PRINCIPAL_APP,
        app=PRINCIPAL_APP,
        num_units=PRINCIPAL_APP_UNITS,
        base=pytestconfig.getoption("--base"),
        constraints=PRINCIAPL_APP_CONSTRAINTS,
    )

    logger.info("Deploying %s", FALCO_APP)
    juju.deploy(charm, app=FALCO_APP)

    logger.info("Integrating %s with %s", PRINCIPAL_APP, FALCO_APP)
    juju.integrate(PRINCIPAL_APP, FALCO_APP)

    logger.info("Waiting for deployment to settle")
    juju.wait(
        lambda status: jubilant.all_active(status, PRINCIPAL_APP, FALCO_APP),
        timeout=juju.wait_timeout,
    )

    logger.info("Deployment complete")
    status = juju.status()

    # Verify ubuntu is deployed
    assert PRINCIPAL_APP in status.apps
    assert status.apps[PRINCIPAL_APP].app_status.current == "active"

    # Verify falco is deployed (as subordinate)
    assert FALCO_APP in status.apps
    units = status.get_units(FALCO_APP)
    assert len(units) == PRINCIPAL_APP_UNITS
    for unit in units.values():
        assert unit.workload_status.current == "active"


def test_falco_files_exist(juju: jubilant.Juju):
    """
    Arrange: Falco charm is deployed and active.
    Act: Check for expected files on the unit.
    Assert: Falco binary, config, and systemd service files exist.
    """
    falco_units = juju.status().get_units(FALCO_APP)
    assert falco_units, "No falco units found"

    for unit_name in falco_units:
        name = unit_name.replace("/", "-")
        logger.info("Checking if falco binary exists in unit %s", unit_name)
        result = juju.ssh(
            unit_name,
            (
                f"test -f /var/lib/juju/agents/unit-{name}/charm/falco/usr/bin/falco"
                " && echo 'exists' || echo 'missing'"
            ),
        )
        assert "exists" in result.strip(), "Falco binary not found"

        logger.info("Checking if falco config exists in unit %s", unit_name)
        result = juju.ssh(
            unit_name,
            (
                f"test -f /var/lib/juju/agents/unit-{name}/charm/falco/etc/falco/falco.yaml"
                " && echo 'exists' || echo 'missing'"
            ),
        )
        assert "exists" in result.strip(), "Falco config file not found"

        logger.info("Checking if falco systemd service exists in unit %s", unit_name)
        result = juju.ssh(
            unit_name,
            "test -f /etc/systemd/system/falco.service && echo 'exists' || echo 'missing'",
        )
        assert "exists" in result.strip(), "Falco systemd service file not found"


def test_falco_service_running(juju: jubilant.Juju):
    """
    Arrange: Falco charm is deployed and active.
    Act: Check if falco systemd service is running.
    Assert: Falco service is active and running.
    """
    falco_units = juju.status().get_units(FALCO_APP)
    assert falco_units, "No falco units found"

    for unit_name in falco_units:
        logger.info("Checking falco service status in unit %s", unit_name)
        result = juju.ssh(unit_name, "systemctl is-active falco")
        assert result.strip() == "active", f"Falco service is not active: {result}"

        logger.info("Checking falco service enabled status in unit %s", unit_name)
        result = juju.ssh(unit_name, "systemctl is-enabled falco")
        assert result.strip() == "enabled", f"Falco service is not enabled: {result}"


def test_remove_integration(juju: jubilant.Juju):
    """
    Arrange: Falco charm is deployed and integrated with a principal charm.
    Act: Remove the integration between falco and the principal charm.
    Assert: Falco service is stopped and files are cleaned up.
    """
    logger.info("Removing integration between %s and %s", PRINCIPAL_APP, FALCO_APP)
    juju.remove_relation(PRINCIPAL_APP, FALCO_APP)
    juju.wait(lambda status: status.apps[PRINCIPAL_APP].is_active, timeout=juju.wait_timeout)

    principal_units = juju.status().get_units(PRINCIPAL_APP)
    for unit_name in principal_units:
        logger.info("Checking if falco service is stopped in unit %s", unit_name)
        result = juju.ssh(unit_name, "systemctl is-active falco || echo 'inactive'")
        assert "inactive" in result or "failed" in result, "Falco service should be inactive"

        logger.info("Checking if falco systemd service file is removed in unit %s", unit_name)
        result = juju.ssh(
            unit_name,
            "test -f /etc/systemd/system/falco.service && echo 'exists' || echo 'missing'",
        )
        assert "missing" in result.strip(), "Falco systemd service file should be removed"
