# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

resource "juju_application" "falcosidekick_k8s" {
  name       = var.app_name
  model_uuid = var.model_uuid

  charm {
    name     = "falcosidekick-k8s"
    base     = var.base
    channel  = var.channel
    revision = var.revision
  }

  units       = var.units
  config      = var.config
  constraints = var.constraints
}
