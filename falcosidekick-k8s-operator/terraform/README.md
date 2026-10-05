# Falcosidekick Terraform module

This folder contains a base [Terraform][Terraform] module for the `falcosidekick-k8s` charm.

- **main.tf** - Defines the Juju application to be deployed.
- **variables.tf** - Allows customization of the deployment. Also models the charm configuration,
  except for exposing the deployment options (Juju model name, channel or application name).
- **output.tf** - Integrates the module with other Terraform modules, primarily
  by defining potential integration endpoints (charm integrations), but also by exposing
  the Juju application name.
- **terraform.tf** - Defines the Terraform provider version.

## Module documentation

<!-- vale off -->
<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
| ---- | ------- |
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | ~> 1.12 |
| <a name="requirement_juju"></a> [juju](#requirement\_juju) | ~> 1.0 |

## Providers

| Name | Version |
| ---- | ------- |
| <a name="provider_juju"></a> [juju](#provider\_juju) | ~> 1.0 |

## Modules

No modules.

## Resources

| Name | Type |
| ---- | ---- |
| [juju_application.falcosidekick](https://registry.terraform.io/providers/juju/juju/latest/docs/resources/application) | resource |

## Inputs

| Name | Description | Type | Default | Required |
| ---- | ----------- | ---- | ------- | :------: |
| <a name="input_app_name"></a> [app\_name](#input\_app\_name) | Name of the application in the Juju model. | `string` | `"falcosidekick-k8s"` | no |
| <a name="input_base"></a> [base](#input\_base) | The operating system on which to deploy | `string` | `null` | no |
| <a name="input_channel"></a> [channel](#input\_channel) | The channel to use when deploying a charm. | `string` | `"2/stable"` | no |
| <a name="input_config"></a> [config](#input\_config) | Application config. Details about available options can be found at https://charmhub.io/falcosidekick-k8s/configurations. | `map(string)` | `{}` | no |
| <a name="input_constraints"></a> [constraints](#input\_constraints) | Juju constraints to apply for this application. | `string` | `null` | no |
| <a name="input_model_uuid"></a> [model\_uuid](#input\_model\_uuid) | The UUID of the Juju model. | `string` | n/a | yes |
| <a name="input_resources"></a> [resources](#input\_resources) | Map of resources to use when deploying the application, e.g. the falcosidekick OCI image. | `map(string)` | `{}` | no |
| <a name="input_revision"></a> [revision](#input\_revision) | Revision number of the charm | `number` | `null` | no |
| <a name="input_units"></a> [units](#input\_units) | Number of units to deploy | `number` | `1` | no |

## Outputs

| Name | Description |
| ---- | ----------- |
| <a name="output_application"></a> [application](#output\_application) | Full juju\_application object for the deployed application. |
| <a name="output_provides"></a> [provides](#output\_provides) | Map of the provided integration endpoints. |
| <a name="output_requires"></a> [requires](#output\_requires) | Map of the required integration endpoints. |
<!-- END_TF_DOCS -->
<!-- vale on -->

## Using `falcosidekick-k8s` base module in a higher level module

If you want to use `falcosidekick-k8s` base module as part of your Terraform module, import it
like shown below:

```text
terraform {
  required_version = ">= 1.12.0"
  required_providers {
    juju = {
      source  = "juju/juju"
      version = ">= 1.1.1"
    }
  }
}

resource "juju_model" "my_model" {
  name = "falcosidekick"
}

module "falcosidekick-k8s" {
  source = "git::https://github.com/canonical/falco-operators.git//falcosidekick-k8s-operator/terraform?ref=falcosidekick-k8s-operator-tf-1.0.0"

  model_uuid = juju_model.my_model.uuid
  channel    = "2/edge"
  # (Customize configuration variables here if needed)
}
```

Create integrations, for instance:

```text
resource "juju_application" "grafana-agent-k8s" {
  model_uuid = juju_model.my_model.uuid
  name       = "grafana-agent-k8s"
  charm {
    name    = "grafana-agent-k8s"
    channel = "2/stable"
    base    = "ubuntu@24.04"
  }

}

resource "juju_integration" "falcosidekick-k8s-grafana-agent-k8s" {
  model_uuid = juju_model.my_model.uuid

  application {
    name     = module.falcosidekick-k8s.application.name
    endpoint = module.falcosidekick-k8s.requires.send_loki_logs.endpoint
  }

  application {
    name     = juju_application.grafana-agent-k8s.name
    endpoint = "logging-provider"
  }
}
```

The complete list of available integrations can be found [in the Integrations tab][falcosidekick-k8s-integrations].

[Terraform]: https://developer.hashicorp.com/terraform
[Terraform Juju provider]: https://registry.terraform.io/providers/juju/juju/latest
[Juju]: https://juju.is
[falcosidekick-k8s-integrations]: https://charmhub.io/falcosidekick-k8s/integrations
