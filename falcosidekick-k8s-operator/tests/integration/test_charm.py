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
