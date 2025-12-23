#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests."""

import logging
import time

import jubilant
import pytest
import requests

logger = logging.getLogger(__name__)

COS_LITE = "cos-lite"
GRAFANA_AGENT_K8S = "grafana-agent-k8s"
FALCOSIDEKICK_APP = "falcosidekick-k8s"
FALCOSIDEKICK_IMAGE = "falcosidekick-image"

COS_LITE_BUNDLE_REVISION = 26
GRAFANA_AGENT_K8S_CHANNEL = "2/stable"
GRAFANA_AGENT_K8S_REVISION = 181


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

    logger.info("Relating %s and %s", FALCOSIDEKICK_APP, GRAFANA_AGENT_K8S)
    juju.integrate(f"{FALCOSIDEKICK_APP}:send-loki-logs", f"{GRAFANA_AGENT_K8S}:logging-provider")

    logger.info("Relating %s to %s applications", GRAFANA_AGENT_K8S, COS_LITE)
    juju.integrate(f"{GRAFANA_AGENT_K8S}:logging-consumer", "loki:logging")
    juju.integrate(f"{GRAFANA_AGENT_K8S}:send-remote-write", "prometheus:receive-remote-write")
    juju.integrate(f"{GRAFANA_AGENT_K8S}:metrics-endpoint", "prometheus:self-metrics-endpoint")

    logger.info("Waiting for deployment to settle")
    juju.wait(
        lambda status: jubilant.all_active(status),
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


def test_send_dummy_logs(juju: jubilant.Juju):
    """
    Arrange: Deploy falcosidekick charm and relate to grafana-agent-k8s.
    Act: Send dummy log via falcosidekick to grafana-agent-k8s.
    Assert: Log is received by loki.
    """
    logger.info("Sending dummy log via grafana-agent-k8s to falcosidekick")
    status = juju.status()
    loki_units = status.get_units("loki")
    falcosidekick_units = status.get_units(FALCOSIDEKICK_APP)

    assert len(loki_units.keys()) == 1, "Only test with single loki unit"
    assert len(falcosidekick_units.keys()) == 1, "Only test with single falcosidekick unit"
    loki_unit = loki_units["loki/0"]
    loki_address = loki_unit.address
    assert loki_address, "Loki unit has no public address"
    falcosidekick_unit = falcosidekick_units[f"{FALCOSIDEKICK_APP}/0"]
    falcosidekick_address = falcosidekick_unit.address
    assert falcosidekick_address, "Falcosidekick unit has no public address"

    # Post to default falcosidekick endpoint
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

    # It might take few seconds for loki to receive the result
    time.sleep(5)

    # Query from default loki endpoint
    resp = requests.get(
        f"http://{loki_address}:3100/loki/api/v1/query_range",
        params={"query": '{rule="Write below binary dir"} |= ``'},
        timeout=10,
    )
    assert resp.ok, f"Loki query failed: {resp.status_code} {resp.text}"
    result = resp.json()
    assert len(result["data"]["result"]) > 0
    assert result["data"]["result"][0]["stream"].get("rule", "") == "Write below binary dir"

    logger.info("Dummy log sent and received successfully")
