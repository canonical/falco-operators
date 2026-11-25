#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for fetching Falco rules from an authenticated OCI registry."""

import logging
import shlex
import uuid
from pathlib import Path

import jubilant

from .helpers import (
    RULES_FILE_NAME,
    RULES_V1_MARKER,
    RULES_V2_MARKER,
    Deployment,
    OciRegistry,
    _installed_rule_files,
    _wait_for_rule,
    _write_rules_file,
)

logger = logging.getLogger(__name__)


def test_wrong_credentials_are_rejected(
    deployment: Deployment,
    juju: jubilant.Juju,
    rules_dir: str,
    registry: OciRegistry,
) -> None:
    """Invalid registry credentials block the charm and install no rules."""
    secret = juju.add_secret(
        f"falco-oci-rules-wrong-{uuid.uuid4().hex[:8]}",
        {
            "username": registry.username,
            "password": "incorrect-password",
            "oci-ref": registry.oci_ref,
        },
        info="OCI rules integration test - incorrect credentials",
    )
    juju.grant_secret(secret, deployment.falco_app)
    juju.config(deployment.falco_app, {"custom-rules-secret": str(secret)})
    status = juju.wait(
        lambda status: jubilant.all_blocked(status, deployment.falco_app),
        timeout=juju.wait_timeout,
        error=jubilant.any_error,
    )
    blocked_units = status.get_units(deployment.falco_app)
    assert blocked_units, "No Falco units found after configuring the wrong secret"
    for blocked_unit in blocked_units.values():
        assert blocked_unit.workload_status.message == "Failed to fetch OCI rules"
    assert not _installed_rule_files(juju, deployment.unit, rules_dir), (
        "Rules were installed despite the registry rejecting the credentials"
    )


def test_valid_credentials_install_rules(
    deployment: Deployment,
    juju: jubilant.Juju,
    rules_dir: str,
    correct_secret,
    registry: OciRegistry,
) -> None:
    """Valid credentials install the rules and return the charm to active."""
    rules = registry.root / "v1" / RULES_FILE_NAME
    _write_rules_file(rules, RULES_V1_MARKER)
    registry.push_rules(rules, "1.0.0")
    juju.wait(
        lambda status: jubilant.all_active(status, deployment.principal_app, deployment.falco_app),
        timeout=juju.wait_timeout,
        error=jubilant.any_error,
    )
    v1_content = _wait_for_rule(
        juju, deployment.unit, rules_dir, RULES_V1_MARKER, timeout=juju.wait_timeout
    )
    assert RULES_V1_MARKER in v1_content
    assert juju.ssh(deployment.unit, "systemctl is-active falcoctl-rules-follow").strip() == (
        "active"
    )


def test_artifact_updates_are_followed(
    deployment: Deployment,
    juju: jubilant.Juju,
    rules_dir: str,
    v2_rules: Path,
) -> None:
    """A new artifact is followed without changing charm configuration."""
    v2_content = _wait_for_rule(juju, deployment.unit, rules_dir, RULES_V2_MARKER, timeout=8 * 60)
    assert RULES_V1_MARKER not in v2_content
    assert juju.ssh(deployment.unit, "systemctl is-active falcoctl-rules-follow").strip() == (
        "active"
    )


def test_recovers_after_network_outage(
    deployment: Deployment,
    juju: jubilant.Juju,
    registry: OciRegistry,
    rules_dir: str,
    v2_rules: Path,
    correct_secret,
) -> None:
    """A network outage blocks the charm, and update-status recovers it."""
    rule_file = Path(rules_dir) / RULES_FILE_NAME
    juju.ssh(deployment.unit, f"sudo -n rm -f {shlex.quote(str(rule_file))}")
    juju.ssh(
        deployment.unit,
        (f"sudo -n iptables -A OUTPUT -d {registry.host} -p tcp --dport {registry.port} -j DROP"),
    )
    try:
        juju.exec("hooks/update-status", unit=deployment.unit, wait=180)
        status = juju.wait(
            lambda status: jubilant.all_blocked(status, deployment.falco_app),
            timeout=juju.wait_timeout,
            error=jubilant.any_error,
        )
        blocked_units = status.get_units(deployment.falco_app)
        assert blocked_units, "No Falco units found after the network outage"
        for blocked_unit in blocked_units.values():
            assert blocked_unit.workload_status.message == "Failed to fetch OCI rules"
        assert not _installed_rule_files(juju, deployment.unit, rules_dir), (
            "Rules were installed while the registry was unreachable"
        )
    finally:
        juju.ssh(
            deployment.unit,
            (
                f"sudo -n iptables -D OUTPUT -d {registry.host} "
                f"-p tcp --dport {registry.port} -j DROP"
            ),
        )

    juju.exec("hooks/update-status", unit=deployment.unit, wait=180)
    juju.wait(
        lambda status: jubilant.all_active(status, deployment.principal_app, deployment.falco_app),
        timeout=juju.wait_timeout,
        error=jubilant.any_error,
    )
    recovered_content = _wait_for_rule(
        juju, deployment.unit, rules_dir, RULES_V2_MARKER, timeout=juju.wait_timeout
    )
    assert RULES_V2_MARKER in recovered_content
    assert juju.ssh(deployment.unit, "systemctl is-active falcoctl-rules-follow").strip() == (
        "active"
    )
