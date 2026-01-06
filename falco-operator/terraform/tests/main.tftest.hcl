# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

variables {
  channel = "0.42/edge"
}

run "test_app_name" {

  command = plan

  assert {
    condition     = module.falco.app_name == "falco"
    error_message = "Expect falco app_name matches 'falco'"
  }
}

run "test_integration_general_info" {

  command = plan

  assert {
    condition     = module.falco.requires.general_info == "general-info"
    error_message = "Expect falco module to provide 'requires.general-info' output"
  }
}
