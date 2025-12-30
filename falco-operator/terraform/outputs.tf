# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "app_name" {
  value       = juju_application.falco.name
  description = "Name of the deployed application."
}

output "general-info" {
  value       = "general-info"
  description = "Endpoint for integrating with any principal charm."
}
