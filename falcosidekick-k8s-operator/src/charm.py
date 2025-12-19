#!/usr/bin/env python3

# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Falcosidekick k8s charm."""

import logging
import typing

import ops

from config import InvalidCharmConfigError
from state import CharmBaseWithState, CharmState
from workload import Falcosidekick

logger = logging.getLogger(__name__)


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

        self.framework.observe(self.on.install, self._install)
        self.framework.observe(self.on.config_changed, self.reconcile)
        self.framework.observe(self.on.falcosidekick_pebble_ready, self.reconcile)

    @property
    def state(self) -> CharmState:
        """Get the charm state.

        Lazily initializes and caches the charm state from the current charm configuration.

        Returns:
            CharmState: The current state of the charm.
        """
        if self._state is None:
            self._state = CharmState.from_charm(self)
        return self._state

    def _install(self, _: ops.EventBase) -> None:
        """Handle the install event.

        Sets the unit status to indicate that containers are being installed.

        Args:
            _: The install event (unused).
        """
        self.unit.status = ops.MaintenanceStatus("Installing containers")

    def reconcile(self, _: ops.EventBase) -> None:
        """Reconcile the charm state.

        Ensures the Falcosidekick workload is configured correctly and running.
        Updates the unit status based on workload readiness and health.

        Args:
            _: The event that triggered reconciliation (unused).

        Raises:
            RuntimeError: If the workload is not healthy after configuration.
        """
        if not self.falcosidekick.ready:
            logger.warning("Pebble is not ready in '%s'", self.falcosidekick.container_name)
            self.unit.status = ops.WaitingStatus("Workload not ready")
            return

        try:
            logger.info("Configuring '%s' workload", self.falcosidekick.container_name)
            self.falcosidekick.configure(self.state)
        except InvalidCharmConfigError as e:
            logger.error("%s", e)
            self.unit.status = ops.BlockedStatus(str(e))
            return

        if not self.falcosidekick.health:
            logger.error("'%s' workload is not healthy", self.falcosidekick.container_name)
            raise RuntimeError("Workload not healthy")

        self.unit.status = ops.ActiveStatus()


if __name__ == "__main__":  # pragma: nocover
    ops.main(FalcosidekickCharm)
