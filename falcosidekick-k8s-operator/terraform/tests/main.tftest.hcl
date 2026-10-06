# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

run "setup_tests" {
  module {
    source = "./tests/setup"
  }
}

run "basic_deploy" {
  variables {
    model_uuid = run.setup_tests.model_uuid
    channel    = "2/edge"
    # renovate: depName="falcosidekick-k8s"
    revision = 60
  }

  assert {
    condition     = output.application.name == "falcosidekick-k8s"
    error_message = "falcosidekick-k8s application name did not match expected"
  }

  assert {
    condition     = output.requires.logging.endpoint == "logging"
    error_message = "falcosidekick-k8s module should provide 'requires.logging' output"
  }

  assert {
    condition     = output.requires.certificates.endpoint == "certificates"
    error_message = "falcosidekick-k8s module should provide 'requires.certificates' output"
  }

  assert {
    condition     = output.requires.ingress.endpoint == "ingress"
    error_message = "falcosidekick-k8s module should provide 'requires.ingress' output"
  }

  assert {
    condition     = output.requires.send_loki_logs.endpoint == "send-loki-logs"
    error_message = "falcosidekick-k8s module should provide 'requires.send_loki_logs' output"
  }

  assert {
    condition     = output.provides.http_endpoint.endpoint == "http-endpoint"
    error_message = "falcosidekick-k8s module should provide 'provides.http_endpoint' output"
  }

  assert {
    condition     = output.provides.grafana_dashboard.endpoint == "grafana-dashboard"
    error_message = "falcosidekick-k8s module should provide 'provides.grafana_dashboard' output"
  }

  assert {
    condition     = output.provides.metrics_endpoint.endpoint == "metrics-endpoint"
    error_message = "falcosidekick-k8s module should provide 'provides.metrics_endpoint' output"
  }
}
