# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

output "application" {
  description = "Full juju_application object for the deployed application."
  value       = juju_application.falcosidekick
}

output "provides" {
  description = "Map of the provided integration endpoints."
  value = {
    grafana_dashboard = {
      kind     = "endpoint"
      name     = juju_application.falcosidekick.name
      endpoint = "grafana-dashboard"
    }
    http_endpoint = {
      kind     = "endpoint"
      name     = juju_application.falcosidekick.name
      endpoint = "http-endpoint"
    }
    metrics_endpoint = {
      kind     = "endpoint"
      name     = juju_application.falcosidekick.name
      endpoint = "metrics-endpoint"
    }
  }
}

output "requires" {
  description = "Map of the required integration endpoints."
  value = {
    certificates = {
      kind     = "endpoint"
      name     = juju_application.falcosidekick.name
      endpoint = "certificates"
    }
    ingress = {
      kind     = "endpoint"
      name     = juju_application.falcosidekick.name
      endpoint = "ingress"
    }
    logging = {
      kind     = "endpoint"
      name     = juju_application.falcosidekick.name
      endpoint = "logging"
    }
    send_loki_logs = {
      kind     = "endpoint"
      name     = juju_application.falcosidekick.name
      endpoint = "send-loki-logs"
    }
  }
}
