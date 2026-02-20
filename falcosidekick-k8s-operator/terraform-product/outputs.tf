# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "falcosidekick_name" {
  description = "Name of the deployed Falco sidekick server application."
  value       = module.falcosidekick.app_name
}

output "falcosidekick_requires" {
  value = {
    certificates   = "certificates"
    logging        = "logging"
    send_loki_logs = "send-loki-logs"
  }
}

output "falcosidekick_provides" {
  value = {
    http_endpoint = "http-endpoint"
  }
}

output "traefik_name" {
  description = "Name of the deployed Traefik application."
  value       = juju_application.traefik_k8s.name
}

output "traefik_requires" {
  value = {
    certificates = "certificates"
    logging      = "logging"
  }
}

output "traefik_provides" {
  value = {
    grafana_dashboard = "grafana-dashboard"
    metrics_endpoint  = "metrics-endpoint"
  }
}
