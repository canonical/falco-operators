# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for Falco charm."""

import ops
import pytest
from ops import testing

from charm import FalcosidekickCharm
from workload import Falcosidekick


class TestCharm:
    """Test Charm class."""

    def test_on_falcosidekick_pebble_ready_cannot_connect(self, loki_relation):
        """Test on falcosidekick pebble ready event when container cannot connect.

        Arrange: Set up mock container that cannot connect.
        Act: Trigger pebble ready event.
        Assert: Charm status is waiting.
        """
        # Arrange: Set up the mock container to simulate a successful connection
        ctx = testing.Context(FalcosidekickCharm)
        # mypy thinks this can_connect argument does not exist.
        container = testing.Container(Falcosidekick.container_name, can_connect=False)  # type: ignore
        state_in = testing.State(containers=[container], relations=[loki_relation])

        # Act: Create a testing context and run the event
        state_out = ctx.run(ctx.on.pebble_ready(container=container), state_in)

        # Assert: Verify that the unit status is set to ActiveStatus
        assert state_out.unit_status == ops.WaitingStatus("Workload not ready")

    @pytest.mark.parametrize(
        "port",
        [
            1,
            80,
            2801,
            8080,
            65535,
        ],
    )
    def test_config_changed_with_valid_port(self, port, loki_relation, certificates_relation):
        """Test config changed event with valid port numbers.

        Arrange: Set up mock container with valid port configuration.
        Act: Trigger config changed event.
        Assert: Charm status is active.
        """
        # Arrange: Set up the mock container and config with valid port
        ctx = testing.Context(FalcosidekickCharm)
        # mypy thinks this can_connect argument does not exist.
        container = testing.Container(Falcosidekick.container_name, can_connect=True)  # type: ignore
        state_in = testing.State(
            containers=[container],
            config={"port": port},
            relations=[loki_relation, certificates_relation],
        )

        # Act: Run the config changed event
        state_out = ctx.run(ctx.on.config_changed(), state_in)

        # Assert: Verify that the unit status is set to ActiveStatus
        assert state_out.unit_status == ops.ActiveStatus()

    @pytest.mark.parametrize(
        "port",
        [
            0,
            -1,
            65536,
            100000,
        ],
    )
    def test_config_changed_with_invalid_port(self, port, loki_relation):
        """Test config changed event with invalid port numbers.

        Arrange: Set up mock container with invalid port configuration.
        Act: Trigger config changed event.
        Assert: Charm status is blocked with invalid config message.
        """
        # Arrange: Set up the mock container and config with invalid port
        ctx = testing.Context(FalcosidekickCharm)
        # mypy thinks this can_connect argument does not exist.
        container = testing.Container(Falcosidekick.container_name, can_connect=True)  # type: ignore
        state_in = testing.State(
            containers=[container], config={"port": port}, relations=[loki_relation]
        )

        # Act: Run the config changed event
        state_out = ctx.run(ctx.on.config_changed(), state_in)
        # Assert: Verify that the unit status is set to BlockedStatus due to invalid config
        assert state_out.unit_status == ops.BlockedStatus("Invalid charm configuration: port")

    @pytest.mark.parametrize(
        "has_loki, has_cert, has_ingress, expected_status",
        [
            (True, True, False, ops.ActiveStatus()),
            (True, False, True, ops.BlockedStatus("Required one of: [certificates|ingress]")),
            (True, True, True, ops.ActiveStatus()),
            (True, False, False, ops.BlockedStatus("Required one of: [certificates|ingress]")),
            (False, True, False, ops.BlockedStatus("Required relations: [send-loki-logs]")),
            (False, False, True, ops.BlockedStatus("Required relations: [send-loki-logs]")),
            (False, True, True, ops.BlockedStatus("Required relations: [send-loki-logs]")),
            (False, False, False, ops.BlockedStatus("Required relations: [send-loki-logs]")),
        ],
    )
    def test_charm_with_different_required_relations(
        self,
        has_loki,
        has_cert,
        has_ingress,
        expected_status,
        loki_relation,
        certificates_relation,
        ingress_relation,
    ):
        """Test charm behavior in various combination of required relation scenarios.

        Arrange: Set up testing context with various relation combinations.
        Act: Run config changed event.
        Assert: Charm status matches expected status based on relation presence.
        """
        ctx = testing.Context(FalcosidekickCharm)
        # mypy thinks this can_connect argument does not exist.
        container = testing.Container(Falcosidekick.container_name, can_connect=True)  # type: ignore
        relations = []
        if has_loki:
            relations.append(loki_relation)
        if has_cert:
            relations.append(certificates_relation)
        if has_ingress:
            relations.append(ingress_relation)
        state_in = testing.State(
            containers=[container],
            relations=relations,
        )

        state_out = ctx.run(ctx.on.config_changed(), state_in)
        assert state_out.unit_status == expected_status
