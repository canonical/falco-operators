---
myst:
  html_meta:
    "description lang=en": "A collection of Juju charms for Falco."
---

<!-- vale Canonical.007-Headings-sentence-case = NO -->

# Falco operators

<!-- vale Canonical.007-Headings-sentence-case = YES -->

A collection of [Juju](https://juju.is/) [charms](https://documentation.ubuntu.com/juju/3.6/reference/charm/)
for deploying and managing [Falco](https://falco.org/) runtime security monitoring. This repository contains:

- **Falco operator**: A subordinate charm that deploys Falco on physical or virtual machines
- **Falcosidekick K8s operator**: A Kubernetes charm that receives and forwards Falco alerts to various outputs

Falco is an open-source cloud native security tool that provides runtime security across hosts, containers,
Kubernetes, and cloud environments. Falcosidekick connects Falco to your ecosystem by forwarding alerts
to observability platforms, incident response tools, and other integrations.

Like any Juju charm, these charms support one-line deployment, configuration, integration, and scaling.

These charms make operating Falco and Falcosidekick simple and straightforward for DevOps or SRE teams through
Juju's clean interface. For information about how to deploy, integrate, and manage these charms, see
the Official [Falco Operator Documentation](https://documentation.ubuntu.com/falco-operators).

## In this documentation

Use the following guides to move from first deployment to ongoing operations, integrations, and security hardening.

```{list-table}
:header-rows: 1
:widths: 15 30

* -
  -
* - **Get started**
  - {ref}`Deploy Falco operator <tutorial_getting_started>` | {ref}`Deploy Falcosidekick K8s operator <tutorial_deploy_falcosidekick>` | {ref}`Connect Falco to Falcosidekick <tutorial_end_to_end>`
* - **Customize runtime detection**
  - {ref}`Configure custom repository <how_to_configure_custom_repository>` | {ref}`Configurations <reference_configurations>` | {ref}`Actions <reference_actions>`
* - **Integrations and observability**
  - {ref}`Integrate with the Canonical Observability Stack <how_to_integrate_with_cos>` | {ref}`Integration endpoints <reference_integrations>` | {ref}`Metrics <reference_metrics>`
* - **Operations**
  - {ref}`Troubleshooting <how_to_troubleshoot>` | {ref}`Upgrade <how_to_upgrade>` | {ref}`Backup and restore <reference_back_up_restore>`
* - **Design**
  - {ref}`Architecture <reference_architecture>` | {ref}`Charm design <explanation_charm_design>`
* - **Security**
  - {ref}`Security overview <explanation_security>` | {ref}`Configure TLS termination with ingress <how_to_configure_tls_ingress>`
```

## How this documentation is organized

This documentation uses the
[Diátaxis documentation structure](https://diataxis.fr/).

- The {ref}`Tutorial <tutorial>` section walks through end-to-end deployments of Falco, Falcosidekick, and their alert pipeline.
- The {ref}`How to <how_to>` section covers practical tasks for configuring integrations, managing runtime rules, troubleshooting issues, and upgrading the charms.
- The {ref}`Reference <reference>` section provides technical details on configurations, actions, integrations, metrics, architecture, and backup expectations.
- The {ref}`Explanation <explanation>` section gives background on the charm design and the security model behind the operators.
- The {ref}`Changelog <changelog>` records notable user-facing documentation changes over time.

## Contributing to this documentation

Documentation is an important part of this project, and we take the same open-source approach to
the documentation as the code. As such, we welcome community contributions, suggestions, and
constructive feedback on our documentation. See {ref}`How to contribute <how_to_contribute>` for more
information.

If there's a particular area of documentation that you'd like to see that's missing, please
[file a bug](https://github.com/canonical/falco-operators/issues).

## Project and community

The Falco Operators are members of the Ubuntu family. This is an open-source project that warmly welcomes community
projects, contributions, suggestions, fixes, and constructive feedback.

- [Code of conduct](https://ubuntu.com/community/code-of-conduct)
- [Get support](https://discourse.charmhub.io/)
- [Join our online chat](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)
- [Contribute](https://github.com/canonical/falco-operators/blob/main/CONTRIBUTING.md)

Thinking about using the Falco Operators for your next project?
[Get in touch](https://matrix.to/#/#charmhub-charmdev:ubuntu.com)!

```{toctree}
:hidden:
tutorial/index.md
how-to/index.md
reference/index.md
explanation/index.md
changelog.md
```
