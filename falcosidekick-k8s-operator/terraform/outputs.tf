# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "app_name" {
  value       = juju_application.falcosidekick.name
  description = "Name of the deployed application."
}

output "requires" {
  value = {
    logging      = "logging"
    certificates = "certificates"
    ingress      = "ingress"
  }
}

output "provides" {
  value = {
    http_endpoint = "http-endpoint"
  }
}
