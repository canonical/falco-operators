# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "app_name" {
  value       = juju_application.falcosidekick_k8s.name
  description = "Name of the deployed application."
}

output "requires" {
  value = {
    send_loki_logs = "send-loki-logs"
    certificates   = "certificates"
  }
}

output "provides" {
  value = {
    http_endpoint = "http-endpoint"
  }
}
