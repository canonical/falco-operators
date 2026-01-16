#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests."""

import logging

import jubilant
import pytest
import requests

logger = logging.getLogger(__name__)

COS_LITE = "cos-lite"
COS_LITE_BUNDLE_REVISION = 26

GRAFANA_AGENT_K8S = "grafana-agent-k8s"
GRAFANA_AGENT_K8S_CHANNEL = "2/stable"
GRAFANA_AGENT_K8S_REVISION = 181

SELF_SIGNED_CERTIFICATE = "self-signed-certificates"
SELF_SIGNED_CERTIFICATE_CHANNEL = "1/stable"
SELF_SIGNED_CERTIFICATE_REVISION = 317

LOKI = "loki"
PROMETHEUS = "prometheus"

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
    logger.info("Deploying %s", COS_LITE)
    juju.deploy(
        COS_LITE,
        trust=True,
        revision=COS_LITE_BUNDLE_REVISION,
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

    logger.info("Relating %s to %s applications", GRAFANA_AGENT_K8S, COS_LITE)
    juju.integrate(f"{GRAFANA_AGENT_K8S}:logging-consumer", f"{LOKI}:logging")
    juju.integrate(f"{GRAFANA_AGENT_K8S}:send-remote-write", f"{PROMETHEUS}:receive-remote-write")
    juju.integrate(f"{GRAFANA_AGENT_K8S}:metrics-endpoint", f"{PROMETHEUS}:self-metrics-endpoint")

    logger.info("Relating %s and %s", FALCOSIDEKICK_K8S, SELF_SIGNED_CERTIFICATE)
    juju.integrate(f"{FALCOSIDEKICK_K8S}:certificates", f"{SELF_SIGNED_CERTIFICATE}:certificates")

    logger.info("Waiting for deployment to settle")
    juju.wait(
        lambda status: jubilant.all_active(status),
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


def test_send_dummy_logs(juju: jubilant.Juju):
    """
    Arrange: Deploy falcosidekick charm and relate to grafana-agent-k8s.
    Act: Send dummy log via falcosidekick to grafana-agent-k8s.
    Assert: Log is received by loki.
    """
    logger.info("Sending dummy log via grafana-agent-k8s to falcosidekick")
    status = juju.status()

    # Get loki address
    loki_units = status.get_units(LOKI)
    assert len(loki_units.keys()) == 1, "Only test with single loki unit"
    loki_unit = loki_units[f"{LOKI}/0"]
    loki_address = loki_unit.address
    assert loki_address, "Loki unit has no public address"

    # Get falcosidekick address
    falcosidekick_units = status.get_units(FALCOSIDEKICK_K8S)
    assert len(falcosidekick_units.keys()) == 1, "Only test with single falcosidekick unit"
    falcosidekick_unit = falcosidekick_units[f"{FALCOSIDEKICK_K8S}/0"]
    falcosidekick_address = falcosidekick_unit.address
    assert falcosidekick_address, "Falcosidekick unit has no public address"

    # Post to default falcosidekick endpoint (port 2801 via http should fail as TLS is enforced)
    try:
        requests.post(
            f"http://{falcosidekick_address}:2801",
            json={
                "output": "16:31:56.746609046: Error File below a known binary directory opened for writing (user=root command=touch /bin/hack file=/bin/hack)",
                "hostname": "localhost",
                "priority": "Error",
                "rule": "Write below binary dir",
                "time": "2019-05-17T15:31:56.746609046Z",
                "output_fields": {
                    "evt.time": 1507591916746609046,
                    "fd.name": "/bin/hack",
                    "proc.cmdline": "touch /bin/hack",
                    "user.name": "root",
                    "container": "falcosidekick",
                },
            },
            timeout=10,
        )
    except requests.exceptions.RequestException as e:
        logger.info("Expected connection error when sending log via http: %s", e)

    resp = requests.get(
        f"http://{falcosidekick_address}:2810/ping",
        timeout=10,
    )

    # /ping should be serving at 2810 when TLS is enforced
    assert resp.ok, "/ping should be reachable via http on port 2810 when TLS is enforced"
