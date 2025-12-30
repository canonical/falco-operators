# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

variables {
  channel = "2/edge"
}

run "test_app_name" {

  command = plan

  assert {
    condition     = module.falcosidekick-k8s.app_name == "falcosidekick-k8s"
    error_message = "Expect falcosidekick-k8s app_name matches 'falcosidekick-k8s'"
  }
}

run "test_integration_send_loki_logs" {

  command = plan

  assert {
    condition     = module.falcosidekick-k8s.send-loki-logs == "send-loki-logs"
    error_message = "Expect falcosidekick-k8s module to provide 'send-loki-logs' output"
  }
}
