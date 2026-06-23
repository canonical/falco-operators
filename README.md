# Falco operators

This repository provides a collection of operators related to [Falco](https://falco.org/).

This repository contains the code for the following charms:

1. [`falco-operator`](./falco-operator): A machine charm deploying and managing [Falco](https://falco.org/)
2. [`falcosidekick-k8s-operator`](./falcosidekick-k8s-operator): A kubernetes charm deploying and managing [Falcosidekick](https://github.com/falcosecurity/falcosidekick/tree/master)

This repository also contains the code for the following charm interfaces:

1. [`falcosidekick_http_endpoint`](./interfaces/falcosidekick_http_endpoint): An interface for connecting charms to Falcosidekick HTTP endpoint.

In addition to charm related code, this repository also contains packages to the aforementioned charms.

1. [`falco`](.github/workflows/build_falco.yaml): A customized Falco package built from source.
2. [`falcocsidekick`](./falcosidekick-k8s-operator/rock): A customized Falcosidekick rock image built from source.

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
