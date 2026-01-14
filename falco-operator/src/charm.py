#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Falco subordinate charm."""

import logging
import typing

import ops
from charmlibs.interfaces.http_endpoint import HttpEndpointRequirer

from certificate import CertificateTransferRequirer
from config import InvalidCharmConfigError
from service import (
    FalcoConfigFile,
    FalcoConfigurationError,
    FalcoCustomSetting,
    FalcoLayout,
    FalcoService,
    FalcoServiceFile,
)
from state import CaCertificateRequiredError, CharmBaseWithState, CharmState

logger = logging.getLogger(__name__)

HTTP_ENDPOINT_RELATION_NAME = "http-endpoint"
CERTIFICATE_TRANSFER_RELATION_NAME = "receive-ca-cert"


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
        self.cert_transfer_requirer = CertificateTransferRequirer(
            self, relation_name=CERTIFICATE_TRANSFER_RELATION_NAME
        )

        self.falco_layout = FalcoLayout(base_dir=self.charm_dir / "falco")
        self.falco_service_file = FalcoServiceFile(self.falco_layout, self)
        self.managed_falco_config = FalcoConfigFile(self.falco_layout)
        self.custom_falco_setting = FalcoCustomSetting(self.falco_layout)
        self.falco_service = FalcoService(
            self.managed_falco_config, self.falco_service_file, self.custom_falco_setting
        )

        self.framework.observe(self.on.remove, self._on_remove)
        self.framework.observe(self.on.install, self._on_install_or_upgrade)
        self.framework.observe(self.on.upgrade_charm, self._on_install_or_upgrade)

        self.framework.observe(self.on.config_changed, self.reconcile)
        self.framework.observe(self.on.secret_changed, self.reconcile)

        # Observe http-endpoint relation evnents to trigger reconciliation
        self.framework.observe(
            self.on[HTTP_ENDPOINT_RELATION_NAME].relation_broken, self.reconcile
        )
        self.framework.observe(
            self.on[HTTP_ENDPOINT_RELATION_NAME].relation_changed, self.reconcile
        )

        # Observe certificate-transfer relation events to trigger reconciliation
        self.framework.observe(
            self.cert_transfer_requirer._certificate_transfer_requirer.on.certificates_removed,
            self.reconcile,
        )
        self.framework.observe(
            self.cert_transfer_requirer._certificate_transfer_requirer.on.certificate_set_updated,
            self.reconcile,
        )

    @property
    def state(self) -> CharmState:
        """The charm state."""
        if self._state is None:
            self._state = CharmState.from_charm(
                self,
                self.http_endpoint_requirer,
                self.cert_transfer_requirer,
            )
        return self._state

    def _on_remove(self, _: ops.RemoveEvent) -> None:
        """Handle remove event."""
        self.unit.status = ops.MaintenanceStatus("Removing Falco service")
        self.falco_service.remove()

    def _on_install_or_upgrade(self, _: ops.InstallEvent | ops.UpgradeCharmEvent) -> None:
        """Handle install or upgrade charm event."""
        self.unit.status = ops.MaintenanceStatus("Installing Falco service")
        self.falco_service.install()

    def reconcile(self, _: ops.EventBase) -> None:
        """Reconcile the charm state."""
        try:
            self.falco_service.configure(self.state, self.cert_transfer_requirer)
        except InvalidCharmConfigError:
            self.unit.status = ops.BlockedStatus("Invalid charm config")
            return
        except CaCertificateRequiredError:
            self.unit.status = ops.BlockedStatus(
                f"Required relations: [{CERTIFICATE_TRANSFER_RELATION_NAME}]"
            )
            return
        except FalcoConfigurationError:
            self.unit.status = ops.BlockedStatus("Failed configuring Falco")
            return

        if not self.falco_service.check_active():
            raise RuntimeError("Falco service is not running")

        self.unit.status = ops.ActiveStatus()


if __name__ == "__main__":  # pragma: nocover
    ops.main(Falco)
