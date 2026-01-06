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

variable "channel" {
  description = "The channel to use when deploying a charm."
  type        = string
  default     = "2/edge"
}

variable "revision" {
  description = "Revision number of the charm."
  type        = number
  default     = null
}

resource "juju_model" "test_model" {
  name = "test-falcosidekick"
}

module "falcosidekick_k8s" {
  source     = "./.."
  app_name   = "falcosidekick-k8s"
  channel    = var.channel
  revision   = var.revision
  model_uuid = juju_model.test_model.uuid
}
