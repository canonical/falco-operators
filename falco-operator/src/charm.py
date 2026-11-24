#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Falco subordinate charm."""

import logging
import typing

import ops
from charms.grafana_agent.v0.cos_agent import COSAgentProvider
from pfe.interfaces.falcosidekick_http_endpoint import HttpEndpointRequirer

from config import ConflictingRulesSourceError, InvalidCharmConfigError
from service import (
    FalcoConfigFile,
    FalcoConfigurationError,
    FalcoCustomSetting,
    FalcoLayout,
    FalcoProxyEnvFile,
    FalcoService,
    FalcoServiceFile,
)
from state import CharmBaseWithState, CharmState

logger = logging.getLogger(__name__)

METRICS_PORT = 8765
HTTP_ENDPOINT_RELATION_NAME = "http-endpoint"


class Falco(CharmBaseWithState):
    """Falco subordinate charm.

    This charm deploys and manages Falco, an open-source runtime security tool.
    As a subordinate charm, it runs alongside a principal charm.
    """

    def __init__(self, *args: typing.Any):
        """Charm the service."""
        super().__init__(*args)

        self._state = None

        self.http_endpoint_requirer = HttpEndpointRequirer(
            self, relation_name=HTTP_ENDPOINT_RELATION_NAME
        )

        self._cos_agent = COSAgentProvider(
            self,
            metrics_endpoints=[
                {"path": "/metrics", "port": METRICS_PORT},
            ],
        )

        self.falco_layout = FalcoLayout(base_dir=self.charm_dir / "falco")
        self.falco_service_file = FalcoServiceFile(self.falco_layout, self)
        self.falco_proxy_env_file = FalcoProxyEnvFile(self.falco_layout, self.model.proxy_config)
        self.managed_falco_config = FalcoConfigFile(self.falco_layout)
        self.custom_falco_setting = FalcoCustomSetting(self.falco_layout)
        self.falco_service = FalcoService(
            self.managed_falco_config,
            self.falco_service_file,
            self.falco_proxy_env_file,
            self.custom_falco_setting,
        )

        self.framework.observe(self.on.remove, self._on_remove)
        self.framework.observe(self.on.install, self._on_install_or_upgrade)
        self.framework.observe(self.on.upgrade_charm, self._on_install_or_upgrade)

        self.framework.observe(self.on.config_changed, self.reconcile)
        self.framework.observe(self.on.secret_changed, self.reconcile)
        self.framework.observe(self.on.retry_oci_rules_action, self._on_retry_oci_rules_action)

        # Observe http-endpoint relation evnents to trigger reconciliation
        self.framework.observe(
            self.on[HTTP_ENDPOINT_RELATION_NAME].relation_broken, self.reconcile
        )
        self.framework.observe(
            self.on[HTTP_ENDPOINT_RELATION_NAME].relation_changed, self.reconcile
        )

    @property
    def state(self) -> CharmState:
        """The charm state."""
        if self._state is None:
            self._state = CharmState.from_charm(self, self.http_endpoint_requirer)
        return self._state

    def _on_remove(self, _: ops.RemoveEvent) -> None:
        """Handle remove event."""
        self.unit.status = ops.MaintenanceStatus("Removing Falco service")
        self.falco_service.remove()

    def _on_install_or_upgrade(self, _: ops.InstallEvent | ops.UpgradeCharmEvent) -> None:
        """Handle install or upgrade charm event."""
        self.unit.status = ops.MaintenanceStatus("Installing Falco service")
        self.falco_service.install()

    def reconcile(self, _: ops.EventBase, force_restart: bool = False) -> bool:
        """Reconcile the charm state.

        Args:
            force_restart: Whether to force the OCI follower to retry immediately.

        Returns:
            True if reconciliation succeeded.
        """
        try:
            self.falco_service.configure(self.state, force_restart=force_restart)
        except ConflictingRulesSourceError as e:
            self.unit.status = ops.BlockedStatus(str(e))
            return False
        except InvalidCharmConfigError as e:
            logger.warning("Invalid charm config: %s", e)
            self.unit.status = ops.BlockedStatus("Invalid charm config")
            return False
        except FalcoConfigurationError:
            self.unit.status = ops.BlockedStatus("Failed configuring Falco")
            return False

        if not self.falco_service.check_active():
            raise RuntimeError("Falco service is not running")

        self.unit.status = ops.ActiveStatus()
        return True

    def _on_retry_oci_rules_action(self, event: ops.ActionEvent) -> None:
        """Retry fetching the configured OCI rules."""
        try:
            if not self.state.custom_rules:
                event.fail("No custom rules secret is configured")
                return
        except (ConflictingRulesSourceError, InvalidCharmConfigError) as e:
            event.fail(str(e))
            return

        try:
            succeeded = self.reconcile(event, force_restart=True)
        except Exception as e:
            logger.exception("Retrying OCI rules failed")
            event.fail(str(e))
            return

        if not succeeded:
            event.fail(self.unit.status.message or "OCI rules retry failed")
            return

        event.set_results({"result": "OCI rules retry completed"})


if __name__ == "__main__":  # pragma: nocover
    ops.main(Falco)
