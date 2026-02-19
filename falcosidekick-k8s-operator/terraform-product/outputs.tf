# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "falcosidekick_name" {
  description = "Name of the deployed Falco sidekick server application."
  value       = module.falcosidekick.app_name
}

output "falcosidekick_http_endpoint_offer_url" {
  value = juju_offer.falcosidekick_http_endpoint.url
}

output "falcosidekick_requires" {
  value = {
    logging      = "logging"
    certificates = "certificates"
  }
}

output "falcosidekick_provides" {
  value = {}
}

output "traefik_name" {
  description = "Name of the deployed Traefik application."
  value       = juju_application.traefik_k8s.name
}

output "traefik_requires" {
  value = {
    logging = "logging"
  }
}

output "traefik_provides" {
  value = {
    grafana_dashboard = "grafana-dashboard"
    metrics_endpoint  = "metrics-endpoint"
  }
}
