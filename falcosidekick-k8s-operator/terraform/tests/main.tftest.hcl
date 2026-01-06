# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

variables {
  channel = "2/edge"
}

run "test_app_name" {

  command = plan

  assert {
    condition     = module.falcosidekick_k8s.app_name == "falcosidekick-k8s"
    error_message = "Expect falcosidekick-k8s app_name matches 'falcosidekick-k8s'"
  }
}

run "test_integration_send_loki_logs" {

  command = plan

  assert {
    condition     = module.falcosidekick_k8s.requires.send_loki_logs == "send-loki-logs"
    error_message = "Expect falcosidekick-k8s module to provide 'requires.send_loki_logs' output"
  }
}

run "test_integration_http_endpoint" {

  command = plan

  assert {
    condition     = module.falcosidekick_k8s.provides.http_endpoint == "http-endpoint"
    error_message = "Expect falcosidekick-k8s module to provide 'provides.http_endpoint' output"
  }
}
