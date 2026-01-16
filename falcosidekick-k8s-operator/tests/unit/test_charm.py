# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for Falco charm."""

from unittest.mock import patch

import ops
import pytest
from ops import testing

from charm import FalcosidekickCharm
from workload import Falcosidekick


class TestCharm:
    """Test Charm class."""

    def test_on_falcosidekick_pebble_ready_can_connect(self, loki_relation, certificates_relation):
        """Test on falcosidekick pebble ready event when container can connect.

        Arrange: Set up mock container that can connect.
        Act: Trigger pebble ready event.
        Assert: Charm status is active.
        """
        # Arrange: Set up the mock container to simulate a successful connection
        ctx = testing.Context(FalcosidekickCharm)
        # mypy thinks this can_connect argument does not exist.
        container = testing.Container(Falcosidekick.container_name, can_connect=True)  # type: ignore
        state_in = testing.State(
            containers=[container], relations=[loki_relation, certificates_relation]
        )

        # Act: Create a testing context and run the event
        state_out = ctx.run(ctx.on.pebble_ready(container=container), state_in)

        # Assert: Verify that the unit status is set to ActiveStatus
        assert state_out.unit_status == ops.ActiveStatus()

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

    def test_charm_with_loki_relation(self, loki_relation, certificates_relation):
        """Test charm behavior when loki relation is present.

        Arrange: Set up testing context with charm and loki relation.
        Act: Run config changed event.
        Assert: Charm initializes successfully with loki relation.
        """
        ctx = testing.Context(FalcosidekickCharm)
        # mypy thinks this can_connect argument does not exist.
        container = testing.Container(Falcosidekick.container_name, can_connect=True)  # type: ignore
        state_in = testing.State(
            containers=[container], relations=[loki_relation, certificates_relation]
        )

        state_out = ctx.run(ctx.on.config_changed(), state_in)

        assert state_out.unit_status == ops.ActiveStatus()

    def test_charm_without_loki_relation(self):
        """Test charm behavior when loki relation is absent.

        Arrange: Set up testing context with charm but no loki relation.
        Act: Run config changed event.
        Assert: Charm initializes successfully without loki relation.
        """
        ctx = testing.Context(FalcosidekickCharm)
        # mypy thinks this can_connect argument does not exist.
        container = testing.Container(Falcosidekick.container_name, can_connect=True)  # type: ignore
        state_in = testing.State(containers=[container], relations=[])

        state_out = ctx.run(ctx.on.config_changed(), state_in)

        assert state_out.unit_status == ops.BlockedStatus("Required relations: [send-loki-logs]")

    @patch("workload.HttpEndpointProvider.update_config")
    def test_charm_with_http_endpoint_relation(
        self,
        mock_update_config,
        loki_relation,
        http_endpoint_relation,
        certificates_relation,
    ):
        """Test charm behavior with http-endpoint relation.

        Arrange: Set up testing context with loki and http-endpoint relations.
        Act: Run config changed event.
        Assert: Http endpoint provider is configured with correct parameters.
        """
        ctx = testing.Context(FalcosidekickCharm)
        # mypy thinks this can_connect argument does not exist.
        container = testing.Container(Falcosidekick.container_name, can_connect=True)  # type: ignore
        state_in = testing.State(
            containers=[container],
            relations=[loki_relation, http_endpoint_relation, certificates_relation],
        )

        state_out = ctx.run(ctx.on.config_changed(), state_in)

        # Verify http endpoint provider was called with correct parameters
        mock_update_config.assert_called_with(
            path="/", scheme="https", listen_port=2801, set_ports=True
        )
        assert state_out.unit_status == ops.ActiveStatus()

    @patch("workload.HttpEndpointProvider.update_config")
    def test_charm_with_http_endpoint_and_tls_relations(
        self,
        mock_update_config,
        loki_relation,
        http_endpoint_relation,
        certificates_relation,
    ):
        """Test charm behavior with http-endpoint and TLS certificate relations.

        Arrange: Set up testing context with loki, http-endpoint, and certificates relations.
        Act: Run config changed event.
        Assert: Http endpoint provider is configured with HTTPS scheme.
        """
        ctx = testing.Context(FalcosidekickCharm)
        # mypy thinks this can_connect argument does not exist.
        container = testing.Container(Falcosidekick.container_name, can_connect=True)  # type: ignore
        state_in = testing.State(
            containers=[container],
            relations=[loki_relation, http_endpoint_relation, certificates_relation],
        )

        state_out = ctx.run(ctx.on.config_changed(), state_in)

        # Verify http endpoint provider was called with HTTPS scheme
        mock_update_config.assert_called_with(
            path="/", scheme="https", listen_port=2801, set_ports=True
        )
        assert state_out.unit_status == ops.ActiveStatus()

    @patch("workload.HttpEndpointProvider.update_config")
    def test_charm_without_tls_certificate_relation(
        self,
        mock_update_config,
        loki_relation,
        http_endpoint_relation,
    ):
        """Test charm behavior with http-endpoint and without TLS certificate relation.

        Arrange: Set up testing context with loki and http-endpoint relations.
        Act: Run config changed event.
        Assert: Http endpoint provider is configured with HTTPS scheme.
        """
        ctx = testing.Context(FalcosidekickCharm)
        # mypy thinks this can_connect argument does not exist.
        container = testing.Container(Falcosidekick.container_name, can_connect=True)  # type: ignore
        state_in = testing.State(
            containers=[container],
            relations=[loki_relation, http_endpoint_relation],
        )

        state_out = ctx.run(ctx.on.config_changed(), state_in)
        assert state_out.unit_status == ops.BlockedStatus("Required relations: [certificates]")
