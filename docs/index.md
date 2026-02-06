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

|                                                                                                         |                                                                                                 |
| ------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| {ref}`Tutorial <tutorial>`</br> Get started - a hands-on introduction to using the charms for new users | {ref}`How-to guides <how_to>`</br> Step-by-step guides covering key operations and common tasks |
| {ref}`Reference <reference>`</br> Technical information - specifications, APIs, architecture            | {ref}`Explanation <explanation>`</br> Concepts - discussion and clarification of key topics     |

## Contributing to this documentation

Documentation is an important part of this project, and we take the same open-source approach to
the documentation as the code. As such, we welcome community contributions, suggestions, and
constructive feedback on our documentation. See {ref}`How to contribute <contribute>` for more
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
