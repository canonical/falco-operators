# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
module "falco" {
  source = "git::https://github.com/canonical/falco-operators//falco-operator/terraform?ref=rev63&depth=1"

  model_uuid = var.model_uuid
  channel    = "0.42/edge"
  revision   = 62
}

resource "juju_application" "grafana_agent" {
  name       = var.grafana_agent.app_name
  model_uuid = data.juju_model.wazuh_indexer.uuid
  trust      = true

  charm {
    name     = "grafana-agent"
    channel  = var.grafana_agent.channel
    revision = var.grafana_agent.revision
    base     = var.wazuh_indexer.base
  }
}

resource "juju_integration" "falco_grafana_agent" {
  model_uuid = data.juju_model.wazuh_indexer.uuid

  application {
    name     = module.wazuh_indexer.app_name
    endpoint = module.wazuh_indexer.provides.cos_agent
  }

  application {
    name     = juju_application.grafana_agent.name
    endpoint = "cos-agent"
  }
}