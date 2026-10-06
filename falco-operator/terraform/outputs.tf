# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "application" {
  description = "Full juju_application object for the deployed application."
  value       = juju_application.falco
}

output "provides" {
  description = "Map of the provided integration endpoints."
  value = {
    cos_agent = {
      kind     = "endpoint"
      name     = juju_application.falco.name
      endpoint = "cos-agent"
    }
  }
}

output "requires" {
  description = "Map of the required integration endpoints."
  value = {
    general_info = {
      kind     = "endpoint"
      name     = juju_application.falco.name
      endpoint = "general-info"
    }
    http_endpoint = {
      kind     = "endpoint"
      name     = juju_application.falco.name
      endpoint = "http-endpoint"
    }
  }
}
