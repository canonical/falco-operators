# Falcosidekick K8s operator

A [Juju][Juju] charm deploying and managing [Falcosidekick][Falcosidekick], an open-source daemon
for connecting [Falco][Falco] to your ecosystem.

## Rock image

Falcosidekick-k8s operator uses a [Rock][Rock] image as the charm workload. Please check the
[falcosidekick rock image][falcosidekick rock image] to learn more about it.

## Contributing

Please see the [CONTRIBUTING.md](./CONTRIBUTING.md) for developer guidance.

[Juju]: https://juju.is/
[Falco]: https://github.com/falcosecurity/falco
[Falcosidekick]: https://github.com/falcosecurity/falcosidekick/tree/master
[Rock]: https://documentation.ubuntu.com/rockcraft/stable/explanation/rocks/#explanation-rocks
[falcosidekick rock image]: ./rock/README.md
