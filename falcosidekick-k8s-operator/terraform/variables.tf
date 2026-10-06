# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

variable "app_name" {
  description = "Name of the application in the Juju model."
  type        = string
  default     = "falcosidekick-k8s"
  nullable    = false
}

variable "base" {
  description = "The operating system on which to deploy"
  type        = string
  default     = null
}

variable "channel" {
  description = "The channel to use when deploying a charm."
  type        = string
  default     = "2/stable"
  nullable    = false
}

variable "config" {
  description = "Application config. Details about available options can be found at https://charmhub.io/falcosidekick-k8s/configurations."
  type        = map(string)
  default     = {}
}

variable "constraints" {
  description = "Juju constraints to apply for this application."
  type        = string
  default     = null
}

variable "model_uuid" {
  description = "The UUID of the Juju model."
  type        = string
  nullable    = false
}

variable "resources" {
  description = "Map of resources to use when deploying the application, e.g. the falcosidekick OCI image."
  type        = map(string)
  default     = {}
}

variable "revision" {
  description = "Revision number of the charm"
  type        = number
  default     = null
}

variable "units" {
  description = "Number of units to deploy"
  type        = number
  default     = 1
}
