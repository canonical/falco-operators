# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "app_name" {
  value       = juju_application.falcosidekick-k8s.name
  description = "Name of the deployed application."
}

output "send-loki-logs" {
  value       = "send-loki-logs"
  description = "Endpoint for sending logs to Loki HTTP API compatible targets."
}
