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
    falcosidekick = {
      channel = "2/edge"
      # renovate: depName="falcosidekick-k8s"
      revision = 41
    }
    traefik_k8s = {
      channel = "latest/stable"
      # renovate: depName="traefik-k8s"
      revision = 236
      config = {
        external_hostname = "falcosidekick.example"
      }
    }
  }

  assert {
    condition     = output.falcosidekick_name == "falcosidekick-k8s"
    error_message = "Expect falcosidekick-k8s app_name matches 'falcosidekick-k8s'"
  }

  assert {
    condition     = output.falcosidekick_requires.logging == "logging"
    error_message = "Expect falcosidekick-k8s module to provide 'requires.logging' output"
  }

  assert {
    condition     = output.falcosidekick_requires.certificates == "certificates"
    error_message = "Expect falcosidekick-k8s module to provide 'requires.certificates' output"
  }
}
