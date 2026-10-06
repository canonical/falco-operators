# Falco operators

This repository provides a collection of operators related to [Falco](https://falco.org/).
Falco is an open source runtime security tool that monitors for anomalous activity and
security threats on Linux hosts, containers, and Kubernetes.

For published user documentation, see the official Falco charms documentation at https://canonical.com/juju/docs/falco-charms/.

## Repository layout

```
docs/                                    # Product documentation

falco-operator/                          # Machine charm deploying and managing Falco
  terraform/                             # Terraform module assets for the Falco charm

falcosidekick-k8s-operator/              # Kubernetes charm deploying and managing Falcosidekick
  rock/                                  # Rockcraft definition and README for the Falcosidekick workload rock image
  terraform/                             # Terraform module assets for the Falcosidekick K8s charm

interfaces/                              # Charm relation interface libraries used by this repository
  falcosidekick_http_endpoint/           # Interface library for the Falcosidekick HTTP endpoint relation
```

## Components

This repository contains the code for the following charms:

| Path | Role |
| --- | --- |
| [`falco-operator`](./falco-operator) | A machine charm deploying and managing [Falco](https://falco.org/) |
| [`falcosidekick-k8s-operator`](./falcosidekick-k8s-operator) | A Kubernetes charm deploying and managing [Falcosidekick](https://github.com/falcosecurity/falcosidekick/tree/master) |

This repository also contains the code for the following charm interfaces:

| Path | Role |
| --- | --- |
| [`falcosidekick_http_endpoint`](./interfaces/falcosidekick_http_endpoint) | An interface for connecting charms to Falcosidekick HTTP endpoint. |

In addition to charm related code, this repository also contains packages to the aforementioned charms.

| Path | Role |
| --- | --- |
| [`falco`](./.github/workflows/build_falco.yaml) | A customized Falco package built from source. |
| [`falcosidekick`](./falcosidekick-k8s-operator/rock) | A customized Falcosidekick rock image built from source. |

### Charmhub

| Name | Listing |
| --- | --- |
| `falco` | https://charmhub.io/falco |
| `falcosidekick-k8s` | https://charmhub.io/falcosidekick-k8s |

## Get started

Start with the in-repo tutorials under [`docs/tutorial/`](./docs/tutorial/):

1. [`docs/tutorial/getting-started.md`](./docs/tutorial/getting-started.md) deploys the Falco subordinate charm with a Kubernetes principal charm and OpenTelemetry Collector, then verifies Falco status, logs, and metrics.
2. [`docs/tutorial/deploy-falcosidekick.md`](./docs/tutorial/deploy-falcosidekick.md) bootstraps a Juju controller on a Kubernetes cloud, deploys `falcosidekick-k8s`, and integrates the supporting charms it needs.
3. [`docs/tutorial/end-to-end-deployment.md`](./docs/tutorial/end-to-end-deployment.md) connects Falco to Falcosidekick through the `http-endpoint` relation and verifies alert forwarding.

## Integrations

For the full list of Falco and Falcosidekick K8s integrations, including observability, TLS, ingress, metrics, dashboards, and logging endpoints, see [`docs/reference/integrations.md`](./docs/reference/integrations.md). For the deployment data flow, see [`docs/reference/architecture.md`](./docs/reference/architecture.md).

## Documentation

Our documentation is stored in the `docs` directory and
can be viewed at https://canonical.com/juju/docs/falco-charms/.
It is based on the Canonical Sphinx Stack and hosted on
[Read the Docs](https://about.readthedocs.com/). In structuring, the
documentation employs the [Diátaxis](https://diataxis.fr/) approach.

You may open a pull request with your documentation changes, or you can
[file a bug](https://github.com/canonical/falco-operators/issues) to
provide constructive feedback or suggestions.

To run the documentation locally before submitting your changes:

```bash
cd docs
make run
```

GitHub runs automatic checks on the documentation to verify spelling,
validate links and style guide compliance.

You can (and should) run the same checks locally:

```bash
make spelling
make linkcheck
make vale
make lint-md
```

## Project and community

The Falco operators project is a member of the Ubuntu family. It is an open source project that warmly welcomes
community projects, contributions, suggestions, fixes and constructive feedback.

- [Code of conduct](https://ubuntu.com/community/code-of-conduct)
- [Contribute](https://github.com/canonical/falco-operators/blob/main/CONTRIBUTING.md)
- [Get support](https://discourse.charmhub.io/)
- [Issues](https://github.com/canonical/falco-operators/issues)
- [Matrix](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)

## Licensing and trademark

See [`LICENSE`](LICENSE).
