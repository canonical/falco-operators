# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "app_name" {
  value       = juju_application.falcosidekick.name
  description = "Name of the deployed application."
}

output "requires" {
  value = {
    certificates   = "certificates"
    ingress        = "ingress"
    logging        = "logging"
    send_loki_logs = "send-loki-logs"
  }
}

output "provides" {
  value = {
    http_endpoint = "http-endpoint"
  }
}
