# Falco Terraform module

This folder contains a base [Terraform][Terraform] module for the `falco` charm.

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
| [juju_application.falco](https://registry.terraform.io/providers/juju/juju/latest/docs/resources/application) | resource |

## Inputs

| Name | Description | Type | Default | Required |
| ---- | ----------- | ---- | ------- | :------: |
| <a name="input_app_name"></a> [app\_name](#input\_app\_name) | Name of the application in the Juju model. | `string` | `"falco"` | no |
| <a name="input_base"></a> [base](#input\_base) | The operating system on which to deploy | `string` | `null` | no |
| <a name="input_channel"></a> [channel](#input\_channel) | The channel to use when deploying a charm. | `string` | `"0.42/stable"` | no |
| <a name="input_config"></a> [config](#input\_config) | Application config. Details about available options can be found at https://charmhub.io/falco/configurations. | `map(string)` | `{}` | no |
| <a name="input_constraints"></a> [constraints](#input\_constraints) | Juju constraints to apply for this application. | `string` | `null` | no |
| <a name="input_model_uuid"></a> [model\_uuid](#input\_model\_uuid) | The UUID of the Juju model. | `string` | n/a | yes |
| <a name="input_revision"></a> [revision](#input\_revision) | Revision number of the charm | `number` | `null` | no |

## Outputs

| Name | Description |
| ---- | ----------- |
| <a name="output_application"></a> [application](#output\_application) | Full juju\_application object for the deployed application. |
| <a name="output_provides"></a> [provides](#output\_provides) | Map of the provided integration endpoints. |
| <a name="output_requires"></a> [requires](#output\_requires) | Map of the required integration endpoints. |
<!-- END_TF_DOCS -->
<!-- vale on -->

## Using `falco` base module in higher level modules

If you want to use `falco` base module as part of your Terraform module, import it
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
  name = "falco"
}

module "falco" {
  source = "git::https://github.com/canonical/falco-operators.git//falco-operator/terraform?ref=falco-operator-tf-1.0.0"

  model_uuid = juju_model.my_model.uuid
  channel    = "0.42/edge"

  # (Customize configuration variables here if needed)
}
```

Create integrations, for instance:

```text
resource "juju_application" "ubuntu" {
  model_uuid = juju_model.my_model.uuid
  name       = "ubuntu"

  charm {
    name    = "ubuntu"
    base    = "ubuntu@24.04"
    channel = "latest/stable"
  }

  constraints = "virt-type=virtual-machine"
}

resource "juju_integration" "falco-ubuntu" {
  model_uuid = juju_model.my_model.uuid

  application {
    name     = module.falco.application.name
    endpoint = module.falco.requires.general_info.endpoint
  }

  application {
    name     = juju_application.ubuntu.name
    endpoint = "juju-info"
  }
}
```

The complete list of available integrations can be found [in the Integrations tab][falco-integrations].

[Terraform]: https://developer.hashicorp.com/terraform
[Terraform Juju provider]: https://registry.terraform.io/providers/juju/juju/latest
[Juju]: https://juju.is
[falco-integrations]: https://charmhub.io/falco/integrations
