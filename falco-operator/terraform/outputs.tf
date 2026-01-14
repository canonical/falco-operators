# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "app_name" {
  value       = juju_application.falco.name
  description = "Name of the deployed application."
}

output "requires" {
  value = {
    general_info  = "general-info"
    http_endpoint = "http-endpoint"
  }
}
