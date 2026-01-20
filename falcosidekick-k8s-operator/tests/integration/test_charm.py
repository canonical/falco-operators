#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests."""

import logging

import jubilant
import pytest

logger = logging.getLogger(__name__)

GRAFANA_AGENT_K8S = "grafana-agent-k8s"
GRAFANA_AGENT_K8S_CHANNEL = "2/stable"
GRAFANA_AGENT_K8S_REVISION = 181

SELF_SIGNED_CERTIFICATE = "self-signed-certificates"
SELF_SIGNED_CERTIFICATE_CHANNEL = "1/stable"
SELF_SIGNED_CERTIFICATE_REVISION = 317

FALCOSIDEKICK_K8S = "falcosidekick-k8s"
FALCOSIDEKICK_IMAGE = "falcosidekick-image"

DEPLOY_TIMEOUT = 10 * 60


def test_deploy_charms(juju: jubilant.Juju, charm: str, pytestconfig: pytest.Config):
    """
    Arrange: Deploy falcosidekick charm.
    Act: Wait for deployment to settle.
    Assert: Applications are deployed and active.
    """
    logger.info("Deploying %s", FALCOSIDEKICK_K8S)
    juju.deploy(
        charm,
        resources={FALCOSIDEKICK_IMAGE: pytestconfig.getoption("--falcosidekick-image")},
        app=FALCOSIDEKICK_K8S,
    )
    logger.info("Deploying %s", GRAFANA_AGENT_K8S)
    juju.deploy(
        GRAFANA_AGENT_K8S,
        channel=GRAFANA_AGENT_K8S_CHANNEL,
        revision=GRAFANA_AGENT_K8S_REVISION,
    )
    logger.info("Deploying %s", SELF_SIGNED_CERTIFICATE)
    juju.deploy(
        SELF_SIGNED_CERTIFICATE,
        channel=SELF_SIGNED_CERTIFICATE_CHANNEL,
        revision=SELF_SIGNED_CERTIFICATE_REVISION,
    )

    logger.info("Relating %s and %s", FALCOSIDEKICK_K8S, GRAFANA_AGENT_K8S)
    juju.integrate(f"{FALCOSIDEKICK_K8S}:send-loki-logs", f"{GRAFANA_AGENT_K8S}:logging-provider")

    logger.info("Relating %s and %s", FALCOSIDEKICK_K8S, SELF_SIGNED_CERTIFICATE)
    juju.integrate(f"{FALCOSIDEKICK_K8S}:certificates", f"{SELF_SIGNED_CERTIFICATE}:certificates")

    logger.info("Waiting for deployment to settle")
    juju.wait(
        lambda status: jubilant.all_active(status, FALCOSIDEKICK_K8S),
        timeout=DEPLOY_TIMEOUT,
    )
    juju.wait(
        lambda status: jubilant.all_blocked(status, GRAFANA_AGENT_K8S),
        timeout=DEPLOY_TIMEOUT,
    )

    logger.info("Deployment complete")
    status = juju.status()

    assert FALCOSIDEKICK_K8S in status.apps
    assert status.apps[FALCOSIDEKICK_K8S].app_status.current == "active"


def test_config_change_valid_port(juju: jubilant.Juju):
    """
    Arrange: Deploy falcosidekick charm with default config.
    Act: Change to a valid port, then reset config.
    Assert: Charm is active after port change and remains active after reset.
    """
    logger.info("Changing port to valid value 8080")
    juju.config(FALCOSIDEKICK_K8S, {"port": "8080"})

    logger.info("Waiting for charm to settle after config change")
    juju.wait(
        lambda status: jubilant.all_active(status, FALCOSIDEKICK_K8S),
        timeout=juju.wait_timeout,
    )

    status = juju.status()
    assert status.apps[FALCOSIDEKICK_K8S].app_status.current == "active"

    logger.info("Resetting charm config")
    juju.config(FALCOSIDEKICK_K8S, reset=["port"])

    logger.info("Waiting for charm to settle after config reset")
    juju.wait(
        lambda status: jubilant.all_active(status, FALCOSIDEKICK_K8S),
        timeout=juju.wait_timeout,
    )

    status = juju.status()
    assert status.apps[FALCOSIDEKICK_K8S].app_status.current == "active"


def test_config_change_invalid_port(juju: jubilant.Juju):
    """
    Arrange: Deploy falcosidekick charm with default config.
    Act: Change to an invalid port, verify blocked status, then reset config.
    Assert: Charm is blocked after invalid port change and active after reset.
    """
    logger.info("Changing port to invalid value 0")
    juju.config(FALCOSIDEKICK_K8S, {"port": "0"})

    logger.info("Waiting for charm to enter blocked status")
    juju.wait(
        lambda status: status.apps[FALCOSIDEKICK_K8S].app_status.current == "blocked",
        timeout=juju.wait_timeout,
    )

    status = juju.status()
    assert status.apps[FALCOSIDEKICK_K8S].app_status.current == "blocked"
    assert "Invalid charm configuration" in status.apps[FALCOSIDEKICK_K8S].app_status.message

    logger.info("Resetting charm config")
    juju.config(FALCOSIDEKICK_K8S, reset=["port"])

    logger.info("Waiting for charm to return to active status")
    juju.wait(
        lambda status: jubilant.all_active(status, FALCOSIDEKICK_K8S),
        timeout=juju.wait_timeout,
    )

    status = juju.status()
    assert status.apps[FALCOSIDEKICK_K8S].app_status.current == "active"
