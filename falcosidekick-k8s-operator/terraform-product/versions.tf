# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

terraform {
  required_version = ">= 1.14.0"
  required_providers {
    juju = {
      source  = "juju/juju"
      version = ">= 1.1.1"
    }
  }
}
