#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests."""

import logging

import jubilant

from .helpers import PRINCIPAL_APP_UNITS, Deployment

logger = logging.getLogger(__name__)


def test_deploy_charms(deployment: Deployment, juju: jubilant.Juju) -> None:
    """
    Arrange: Deploy a principal charm with VM constraints and the Falco charm.
    Act: Integrate the Falco charm with the principal charm.
    Assert: Both applications are deployed and active.
    """
    status = juju.status()

    assert deployment.principal_app in status.apps
    assert status.apps[deployment.principal_app].app_status.current == "active"

    assert deployment.falco_app in status.apps
    assert len(deployment.units) == PRINCIPAL_APP_UNITS
    for unit_name in deployment.units:
        unit = status.get_units(deployment.falco_app)[unit_name]
        assert unit.workload_status.current == "active"


def test_falco_files_exist(deployment: Deployment, juju: jubilant.Juju) -> None:
    """
    Arrange: Falco charm is deployed and active.
    Act: Check for expected files on the unit.
    Assert: Falco binary, config, and systemd service files exist.
    """
    for unit_name in deployment.units:
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


def test_falco_service_running(deployment: Deployment, juju: jubilant.Juju) -> None:
    """
    Arrange: Falco charm is deployed and active.
    Act: Check if falco systemd service is running.
    Assert: Falco service is active and running.
    """
    for unit_name in deployment.units:
        logger.info("Checking falco service status in unit %s", unit_name)
        result = juju.ssh(unit_name, "systemctl is-active falco")
        assert result.strip() == "active", f"Falco service is not active: {result}"

        logger.info("Checking falco service enabled status in unit %s", unit_name)
        result = juju.ssh(unit_name, "systemctl is-enabled falco")
        assert result.strip() == "enabled", f"Falco service is not enabled: {result}"


def test_remove_integration(deployment: Deployment, juju: jubilant.Juju) -> None:
    """
    Arrange: Falco charm is deployed and integrated with a principal charm.
    Act: Remove the integration between falco and the principal charm.
    Assert: Falco service is stopped and files are cleaned up.
    """
    logger.info(
        "Removing integration between %s and %s", deployment.principal_app, deployment.falco_app
    )
    juju.remove_relation(deployment.principal_app, deployment.falco_app)
    juju.wait(
        lambda status: status.apps[deployment.principal_app].is_active, timeout=juju.wait_timeout
    )

    for unit_name in deployment.units:
        logger.info("Checking if falco service is stopped in unit %s", unit_name)
        result = juju.ssh(unit_name, "systemctl is-active falco || echo 'inactive'")
        assert "inactive" in result or "failed" in result, "Falco service should be inactive"

        logger.info("Checking if falco systemd service file is removed in unit %s", unit_name)
        result = juju.ssh(
            unit_name,
            "test -f /etc/systemd/system/falco.service && echo 'exists' || echo 'missing'",
        )
        assert "missing" in result.strip(), "Falco systemd service file should be removed"
