# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

variables {
  channel = "latest/edge"
  # renovate: depName="falco"
  revision = 1
}

run "basic_deploy" {
  assert {
    condition     = module.falco.app_name == "falco"
    error_message = "falco app_name did not match expected"
  }
}
