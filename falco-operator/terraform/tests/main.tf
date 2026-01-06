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
  default     = "0.42/edge"
}

variable "revision" {
  description = "Revision number of the charm."
  type        = number
  default     = null
}

resource "juju_model" "test_model" {
  name = "test-falco"
}

module "falco" {
  source     = "./.."
  app_name   = "falco"
  channel    = var.channel
  revision   = var.revision
  model_uuid = juju_model.test_model.uuid
}
