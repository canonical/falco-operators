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
    channel    = "0.42/edge"
    # renovate: depName="falco"
    revision = 69
  }

  assert {
    condition     = output.application.name == "falco"
    error_message = "falco application name did not match expected"
  }

  assert {
    condition     = output.requires.general_info.endpoint == "general-info"
    error_message = "falco module should provide 'requires.general_info' output"
  }

  assert {
    condition     = output.requires.http_endpoint.endpoint == "http-endpoint"
    error_message = "falco module should provide 'requires.http_endpoint' output"
  }

  assert {
    condition     = output.provides.cos_agent.endpoint == "cos-agent"
    error_message = "falco module should provide 'provides.cos_agent' output"
  }
}
