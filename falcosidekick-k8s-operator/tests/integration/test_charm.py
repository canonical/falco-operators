#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests."""

import logging

import jubilant
import pytest

logger = logging.getLogger(__name__)

FALCOSIDEKICK_APP = "falcosidekick"
FALCOSIDEKICK_IMAGE = "falcosidekick-image"


def test_deploy_charms(juju: jubilant.Juju, charm: str, pytestconfig: pytest.Config):
    """
    Arrange: Deploy falcosidekick charm.
    Act: Wait for deployment to settle.
    Assert: Applications are deployed and active.
    """
    logger.info("Deploying %s", FALCOSIDEKICK_APP)
    juju.deploy(
        charm,
        resources={FALCOSIDEKICK_IMAGE: pytestconfig.getoption("--falcosidekick-image")},
        app=FALCOSIDEKICK_APP,
    )

    logger.info("Waiting for deployment to settle")
    juju.wait(
        lambda status: jubilant.all_active(status, FALCOSIDEKICK_APP),
        timeout=juju.wait_timeout,
    )

    logger.info("Deployment complete")
    status = juju.status()

    assert FALCOSIDEKICK_APP in status.apps
    assert status.apps[FALCOSIDEKICK_APP].app_status.current == "active"


def test_config_change_valid_port(juju: jubilant.Juju):
    """
    Arrange: Deploy falcosidekick charm with default config.
    Act: Change to a valid port, then reset config.
    Assert: Charm is active after port change and remains active after reset.
    """
    logger.info("Changing port to valid value 8080")
    juju.config(FALCOSIDEKICK_APP, {"port": "8080"})

    logger.info("Waiting for charm to settle after config change")
    juju.wait(
        lambda status: jubilant.all_active(status, FALCOSIDEKICK_APP),
        timeout=juju.wait_timeout,
    )

    status = juju.status()
    assert status.apps[FALCOSIDEKICK_APP].app_status.current == "active"

    logger.info("Resetting charm config")
    juju.config(FALCOSIDEKICK_APP, reset=["port"])

    logger.info("Waiting for charm to settle after config reset")
    juju.wait(
        lambda status: jubilant.all_active(status, FALCOSIDEKICK_APP),
        timeout=juju.wait_timeout,
    )

    status = juju.status()
    assert status.apps[FALCOSIDEKICK_APP].app_status.current == "active"


def test_config_change_invalid_port(juju: jubilant.Juju):
    """
    Arrange: Deploy falcosidekick charm with default config.
    Act: Change to an invalid port, verify blocked status, then reset config.
    Assert: Charm is blocked after invalid port change and active after reset.
    """
    logger.info("Changing port to invalid value 0")
    juju.config(FALCOSIDEKICK_APP, {"port": "0"})

    logger.info("Waiting for charm to enter blocked status")
    juju.wait(
        lambda status: status.apps[FALCOSIDEKICK_APP].app_status.current == "blocked",
        timeout=juju.wait_timeout,
    )

    status = juju.status()
    assert status.apps[FALCOSIDEKICK_APP].app_status.current == "blocked"
    assert "Invalid charm configuration" in status.apps[FALCOSIDEKICK_APP].app_status.message

    logger.info("Resetting charm config")
    juju.config(FALCOSIDEKICK_APP, reset=["port"])

    logger.info("Waiting for charm to return to active status")
    juju.wait(
        lambda status: jubilant.all_active(status, FALCOSIDEKICK_APP),
        timeout=juju.wait_timeout,
    )

    status = juju.status()
    assert status.apps[FALCOSIDEKICK_APP].app_status.current == "active"
