# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

data "juju_model" "falcosidekick" {
  uuid = var.model_uuid
}

module "falcosidekick" {
  source      = "../terraform"
  app_name        = var.falcosidekick.app_name
  model_uuid  = data.juju_model.falcosidekick.uuid
  base        = var.falcosidekick.base
  channel     = var.falcosidekick.channel
  revision    = var.falcosidekick.revision
  units       = var.falcosidekick.units
  config      = var.falcosidekick.config
  constraints = var.falcosidekick.constraints
}

resource "juju_application" "traefik_k8s" {
  name       = var.traefik_k8s.app_name
  model_uuid = data.juju_model.falcosidekick.uuid
  trust      = true
  charm {
    name     = "traefik-k8s"
    channel  = var.traefik_k8s.channel
    revision = var.traefik_k8s.revision
  }
  units  = var.traefik_k8s.units
  config = var.traefik_k8s.config
}

resource "juju_integration" "wazuh_server_traefik_ingress" {
  model_uuid = data.juju_model.falcosidekick.uuid

  application {
    name     = module.falcosidekick.app_name
    endpoint = module.falcosidekick.requires.ingress
  }

  application {
    name     = juju_application.traefik_k8s.name
    endpoint = "traefik-route"
  }
}
