#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Falco subordinate charm."""

import logging
import typing

import ops

from service import FalcoConfig, FalcoLayout, FalcoService, FalcoServiceFile

logger = logging.getLogger(__name__)


class Charm(ops.CharmBase):
    """Falco subordinate charm.

    This charm deploys and manages Falco, an open-source runtime security tool.
    As a subordinate charm, it runs alongside a principal charm.
    """

    def __init__(self, *args: typing.Any):
        """Charm the service."""
        super().__init__(*args)

        self.falco_layout = FalcoLayout(base_dir=self.charm_dir / "falco")
        self.falco_service_file = FalcoServiceFile(self.falco_layout)
        self.managed_falco_config = FalcoConfig(self.falco_layout, self)
        self.falco_service = FalcoService(self.managed_falco_config, self.falco_service_file)

        self.framework.observe(self.on.remove, self._on_remove)
        self.framework.observe(self.on.install, self._on_install_or_upgrade)
        self.framework.observe(self.on.upgrade_charm, self._on_install_or_upgrade)
        self.framework.observe(self.on.update_status, self._update_status)

    def _on_remove(self, _: ops.RemoveEvent) -> None:
        """Handle remove event."""
        self.unit.status = ops.MaintenanceStatus("Removing Falco service")
        self.falco_service.remove()

    def _on_install_or_upgrade(self, _: ops.InstallEvent | ops.UpgradeCharmEvent) -> None:
        """Handle install or upgrade charm event."""
        self.unit.status = ops.MaintenanceStatus("Installing Falco service")
        self.falco_service.install()
        self.reconcile()

    def _update_status(self, _: ops.UpdateStatusEvent) -> None:
        """Update the unit status."""
        self.reconcile()

    def reconcile(self) -> None:
        """Reconcile the charm state."""
        if not self.falco_service.check_active():
            raise RuntimeError("Falco service is not running")
        self.unit.status = ops.ActiveStatus()


if __name__ == "__main__":  # pragma: nocover
    ops.main(Charm)
