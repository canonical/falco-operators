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
    revision = 41
  }

  assert {
    condition     = output.app_name == "falcosidekick-k8s"
    error_message = "falcosidekick-k8s app_name did not match expected"
  }

  assert {
    condition     = output.requires.logging == "logging"
    error_message = "falcosidekick-k8s module should provide 'requires.logging' output"
  }

  assert {
    condition     = output.requires.certificates == "certificates"
    error_message = "falcosidekick-k8s module should provide 'requires.certificates' output"
  }

  assert {
    condition     = output.requires.ingress == "ingress"
    error_message = "falcosidekick-k8s module should provide 'requires.ingress' output"
  }

  assert {
    condition     = output.provides.http_endpoint == "http-endpoint"
    error_message = "falcosidekick-k8s module should provide 'provides.http_endpoint' output"
  }
}
