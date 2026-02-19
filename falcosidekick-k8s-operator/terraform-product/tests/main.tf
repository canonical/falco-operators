# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

terraform {
  required_version = ">= 1.14.0"
  required_providers {
    juju = {
      version = "~> 1.1.1"
      source  = "juju/juju"
    }
  }
}

provider "juju" {}

module "falcosidekick" {
  source     = "./.."
  model_uuid = juju_model.test_model.uuid

  falcosidekick = {
    channel  = "2/edge"
    revision = 37
  }

  traefik_k8s = {
    channel  = "latest/stable"
    revision = 236
    config = {
      external_hostname = "falcosidekick.example"
    }
  }
}
