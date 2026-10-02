#!/usr/bin/env python3

# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests."""

import logging

import jubilant

logger = logging.getLogger(__name__)

GRAFANA_AGENT_K8S = "grafana-agent-k8s"
GRAFANA_AGENT_K8S_CHANNEL = "2/stable"
GRAFANA_AGENT_K8S_REVISION = 181

FALCOSIDEKICK_K8S = "falcosidekick-k8s"

INGRESS_CHARM = "ingress-configurator"
INGRESS_CHARM_CHANNEL = "stable"
INGRESS_CHARM_REVISION = 78

DEPLOY_TIMEOUT = 10 * 60


def test_deploy_charms(juju: jubilant.Juju, charm: str, charm_resource_images: dict):
    """
    Arrange: Deploy falcosidekick charm.
    Act: Wait for deployment to settle.
    Assert: Applications are deployed and active.
    """
    logger.info("Deploying %s", GRAFANA_AGENT_K8S)
    juju.deploy(
        GRAFANA_AGENT_K8S,
        channel=GRAFANA_AGENT_K8S_CHANNEL,
        revision=GRAFANA_AGENT_K8S_REVISION,
        trust=True,
    )
    logger.info("Deploying %s", INGRESS_CHARM)
    juju.deploy(
        INGRESS_CHARM,
        channel=INGRESS_CHARM_CHANNEL,
        revision=INGRESS_CHARM_REVISION,
        trust=True,
    )
    logger.info("Deploying %s", FALCOSIDEKICK_K8S)
    juju.deploy(
        charm,
        resources=charm_resource_images["falcosidekick-k8s"],
        app=FALCOSIDEKICK_K8S,
    )

    logger.info("Relating %s and %s", FALCOSIDEKICK_K8S, GRAFANA_AGENT_K8S)
    juju.integrate(f"{FALCOSIDEKICK_K8S}:send-loki-logs", f"{GRAFANA_AGENT_K8S}:logging-provider")

    logger.info("Relating %s and %s", FALCOSIDEKICK_K8S, INGRESS_CHARM)
    juju.integrate(f"{FALCOSIDEKICK_K8S}:ingress", f"{INGRESS_CHARM}:ingress")

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
