# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

variable "model_uuid" {
  description = "Juju model UUID."
  type        = string
}

variable "falcosidekick" {
  type = object({
    app_name    = optional(string, "falcosidekick-k8s")
    channel     = optional(string, "2/edge")
    config      = optional(map(string), {})
    constraints = optional(string, "arch=amd64")
    revision    = optional(number)
    base        = optional(string, "ubuntu@24.04")
    units       = optional(number, 1)
    storage     = optional(map(string), {})
  })
}

variable "traefik_k8s" {
  type = object({
    app_name    = optional(string, "traefik-k8s")
    channel     = optional(string, "latest/edge")
    config      = optional(map(string), {})
    constraints = optional(string, "arch=amd64")
    revision    = optional(number)
    base        = optional(string, "ubuntu@24.04")
    units       = optional(number, 1)
    storage     = optional(map(string), {})
  })
}