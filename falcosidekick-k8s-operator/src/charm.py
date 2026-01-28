#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Falcosidekick k8s charm."""

import logging
import typing

import ops
from charms.loki_k8s.v1.loki_push_api import LokiPushApiConsumer
from charms.traefik_k8s.v2.ingress import IngressPerAppRequirer
from pfe.interfaces.falcosidekick_http_endpoint import HttpEndpointProvider

from certificates import TlsCertificateRequirer
from config import InvalidCharmConfigError
from state import CharmBaseWithState, CharmState
from workload import (
    Falcosidekick,
    MissingLokiRelationError,
    RequireOneOfIngressOrCertificateRelationError,
)

logger = logging.getLogger(__name__)

CERTIFICATE_RELATION_NAME = "certificates"
SEND_LOKI_LOG_RELATION_NAME = "send-loki-logs"
HTTP_ENDPOINT_RELATION_NAME = "http-endpoint"
INGRESS_RELATION_NAME = "ingress"


class FalcosidekickCharm(CharmBaseWithState):
    """Falcosidekick k8s charm.

    This charm deploys and manages Falcosidekick, an open-source daemon for connecting Falco to
    your ecosystem.
    """

    def __init__(self, *args: typing.Any):
        """Initialize the Falcosidekick charm.

        Sets up the charm, initializes the workload, and observes relevant events.

        Args:
            *args: Variable length argument list passed to the parent class.
        """
        super().__init__(*args)

        self._state = None

        self.falcosidekick = Falcosidekick(self)
        self.loki_push_api_consumer = LokiPushApiConsumer(
            self,
            relation_name=SEND_LOKI_LOG_RELATION_NAME,
        )
        self.http_endpoint_provider = HttpEndpointProvider(
            self, relation_name=HTTP_ENDPOINT_RELATION_NAME, set_ports=True
        )
        self.tls_certificate_requirer = TlsCertificateRequirer(
            self, relation_name=CERTIFICATE_RELATION_NAME
        )
        self.ingress_requirer = IngressPerAppRequirer(
            self, relation_name=INGRESS_RELATION_NAME, strip_prefix=True, redirect_https=True
        )

        self.framework.observe(self.on.install, self._install)
        self.framework.observe(self.on.config_changed, self.reconcile)
        self.framework.observe(self.on.falcosidekick_pebble_ready, self.reconcile)

        self.framework.observe(
            self.loki_push_api_consumer.on.loki_push_api_endpoint_joined, self.reconcile
        )
        self.framework.observe(
            self.loki_push_api_consumer.on.loki_push_api_endpoint_departed, self.reconcile
        )

        self.framework.observe(
            self.on[HTTP_ENDPOINT_RELATION_NAME].relation_changed, self.reconcile
        )

        self.framework.observe(self.on[CERTIFICATE_RELATION_NAME].relation_broken, self.reconcile)
        self.framework.observe(self.on[CERTIFICATE_RELATION_NAME].relation_changed, self.reconcile)

        self.framework.observe(self.on[INGRESS_RELATION_NAME].relation_broken, self.reconcile)
        self.framework.observe(self.on[INGRESS_RELATION_NAME].relation_changed, self.reconcile)

    @property
    def state(self) -> CharmState:
        """Get the charm state.

        Lazily initializes and caches the charm state from the current charm configuration.

        Returns:
            CharmState: The current state of the charm.
        """
        if self._state is None:
            self._state = CharmState.from_charm(
                self,
                self.loki_push_api_consumer,
                self.ingress_requirer,
            )
        return self._state

    def _install(self, _: ops.EventBase) -> None:
        """Handle the install event.

        Sets the unit status to indicate that containers are being installed.

        Args:
            _: The placeholder for the install event.
        """
        self.unit.status = ops.MaintenanceStatus("Installing containers")

    def reconcile(self, _: ops.EventBase) -> None:
        """Reconcile the charm state.

        Ensures the Falcosidekick workload is configured correctly and running.
        Updates the unit status based on workload readiness and health.

        Args:
            _: A placeholder for the event that triggered the reconciliation.

        Raises:
            RuntimeError: If the workload is not healthy after configuration.
        """
        if not self.falcosidekick.ready:
            logger.warning("Pebble is not ready in '%s'", self.falcosidekick.container_name)
            self.unit.status = ops.WaitingStatus("Workload not ready")
            return

        try:
            logger.info("Configuring '%s' workload", self.falcosidekick.container_name)
            self.falcosidekick.configure(
                self.state,
                self.http_endpoint_provider,
                self.tls_certificate_requirer,
                self.ingress_requirer,
            )
        except InvalidCharmConfigError as e:
            logger.error("%s", e)
            self.unit.status = ops.BlockedStatus(str(e))
            return
        except MissingLokiRelationError as e:
            logger.error("%s", e)
            self.unit.status = ops.BlockedStatus("Required relations: [send-loki-logs]")
            return
        except RequireOneOfIngressOrCertificateRelationError as e:
            logger.error("%s", e)
            self.unit.status = ops.BlockedStatus("Required one of: [certificates|ingress]")
            return

        self.unit.status = ops.ActiveStatus()


if __name__ == "__main__":  # pragma: nocover
    ops.main(FalcosidekickCharm)
