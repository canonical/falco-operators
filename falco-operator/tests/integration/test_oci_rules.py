#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Integration tests for fetching Falco rules from an authenticated OCI registry."""

import logging
import uuid

import jubilant

from .oci_registry import (
    FALCO_APP,
    PRINCIPAL_APP,
    RULE_UPDATE_TIMEOUT,
    RULES_FILE_NAME,
    RULES_REFRESH_INTERVAL,
    RULES_V1_MARKER,
    RULES_V2_MARKER,
    Deployment,
    OciRegistry,
    _block_registry,
    _fire_update_status,
    _install_ca,
    _installed_rule_files,
    _remove_managed_rules,
    _rules_dir,
    _unblock_registry,
    _wait_for_rule,
    _write_rules_file,
)

logger = logging.getLogger(__name__)


def test_oci_rules_with_authenticated_registry(
    deployment: Deployment,
    registry: OciRegistry,
) -> None:
    """
    Arrange: Deploy Falco, start an authenticated TLS OCI registry, and push rules.
    Act: Configure the charm with bad credentials, then with valid credentials, then
        publish an updated rules artifact without changing charm configuration, then
        simulate a registry outage and fire update-status.
    Assert: Bad credentials block the unit, valid credentials install the rules, the
        follower installs the updated rules automatically, a registry outage blocks the
        unit when no rules exist, and update-status restores the rules and active status.
    """
    juju = deployment.juju
    unit = deployment.unit

    _install_ca(juju, unit, registry.ca_cert)
    rules_dir = _rules_dir(juju, unit)

    suffix = uuid.uuid4().hex[:8]
    rules_v1 = registry.root / "v1" / RULES_FILE_NAME
    _write_rules_file(rules_v1, RULES_V1_MARKER)
    registry.push_rules(rules_v1, "1.0.0")

    logger.info("Configuring the charm with an incorrect registry password")
    wrong_secret = juju.add_secret(
        f"falco-oci-rules-wrong-{suffix}",
        {
            "username": registry.username,
            "password": "incorrect-password",
            "oci-ref": registry.oci_ref,
        },
        info="OCI rules integration test - incorrect credentials",
    )
    juju.grant_secret(wrong_secret, FALCO_APP)
    juju.config(
        FALCO_APP,
        {
            "custom-rules-secret": str(wrong_secret),
            "custom-rules-refresh-interval": RULES_REFRESH_INTERVAL,
        },
    )

    status = juju.wait(
        lambda status: jubilant.all_blocked(status, FALCO_APP),
        timeout=juju.wait_timeout,
        error=jubilant.any_error,
    )
    blocked_units = status.get_units(FALCO_APP)
    assert blocked_units, "No Falco units found after configuring the wrong secret"
    for blocked_unit in blocked_units.values():
        assert blocked_unit.workload_status.message == "Failed to fetch OCI rules"
    assert not _installed_rule_files(juju, unit, rules_dir), (
        "Rules were installed despite the registry rejecting the credentials"
    )

    logger.info("Rotating the charm secret to the correct registry password")
    correct_secret = juju.add_secret(
        f"falco-oci-rules-correct-{suffix}",
        {
            "username": registry.username,
            "password": registry.password,
            "oci-ref": registry.oci_ref,
        },
        info="OCI rules integration test - correct credentials",
    )
    juju.grant_secret(correct_secret, FALCO_APP)
    juju.config(FALCO_APP, {"custom-rules-secret": str(correct_secret)})

    juju.wait(
        lambda status: jubilant.all_active(status, PRINCIPAL_APP, FALCO_APP),
        timeout=juju.wait_timeout,
        error=jubilant.any_error,
    )
    v1_content = _wait_for_rule(juju, unit, rules_dir, RULES_V1_MARKER, timeout=juju.wait_timeout)
    assert RULES_V1_MARKER in v1_content
    assert juju.ssh(unit, "systemctl is-active falcoctl-rules-follow").strip() == "active"

    logger.info("Publishing an updated rules artifact; charm configuration is unchanged")
    rules_v2 = registry.root / "v2" / RULES_FILE_NAME
    _write_rules_file(rules_v2, RULES_V2_MARKER)
    registry.push_rules(rules_v2, "1.0.1")

    v2_content = _wait_for_rule(
        juju, unit, rules_dir, RULES_V2_MARKER, timeout=RULE_UPDATE_TIMEOUT
    )
    assert RULES_V1_MARKER not in v2_content
    assert juju.ssh(unit, "systemctl is-active falcoctl-rules-follow").strip() == "active"

    logger.info("Simulating a registry network outage and recovery on update-status")
    _remove_managed_rules(juju, unit, rules_dir)
    _block_registry(juju, unit, registry.host)
    try:
        _fire_update_status(juju, unit)
        status = juju.wait(
            lambda status: jubilant.all_blocked(status, FALCO_APP),
            timeout=juju.wait_timeout,
            error=jubilant.any_error,
        )
        blocked_units = status.get_units(FALCO_APP)
        assert blocked_units, "No Falco units found after the network outage"
        for blocked_unit in blocked_units.values():
            assert blocked_unit.workload_status.message == "Failed to fetch OCI rules"
        assert not _installed_rule_files(juju, unit, rules_dir), (
            "Rules were installed while the registry was unreachable"
        )
    finally:
        _unblock_registry(juju, unit, registry.host)

    logger.info("Restoring the registry and triggering update-status")
    _fire_update_status(juju, unit)
    juju.wait(
        lambda status: jubilant.all_active(status, PRINCIPAL_APP, FALCO_APP),
        timeout=juju.wait_timeout,
        error=jubilant.any_error,
    )
    recovered_content = _wait_for_rule(
        juju, unit, rules_dir, RULES_V2_MARKER, timeout=juju.wait_timeout
    )
    assert RULES_V2_MARKER in recovered_content
    assert juju.ssh(unit, "systemctl is-active falcoctl-rules-follow").strip() == "active"
