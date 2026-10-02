# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

resource "juju_application" "falco" {
  name       = var.app_name
  model_uuid = var.model_uuid

  charm {
    name     = "falco"
    base     = var.base
    channel  = var.channel
    revision = var.revision
  }

  config      = var.config
  constraints = var.constraints
}
