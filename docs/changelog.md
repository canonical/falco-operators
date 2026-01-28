(changelog)=

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

Each revision is versioned by the date of the revision.

## 2026-01-28

Add ingress relation for falcosidekick-k8s-operator. With ingress, the certificates relation is not mandatory, the TLS
terminates at the gateway.

### Added

- Observe and handle ingress relation changed and broken
- Make certificate relation and ingress relation mutually exclusive

### Changed

- Certificate relation changes to optional
- Update terraform module to include ingress relation

## 2026-01-16

Add certificate interface to support falcosidekick-k8s to obtain a certificate from a provider. If falcosidekick-k8s
obtains a certificate, it will start the server with TLS enabled. In additional to that, a HTTP server on port 2810 will
be serving for `/healthz` and `/ping` for internal health check.

### Added

- Add certificate lib and interface to falcosidekick-k8s-operator
- Add logic to handle certificate relation related events to falcosidekick-k8s-operator
  - Observed certificate relation changed and broken event to reconcile the state and update falcosidekick service
  - Refresh the certificate state when the falcosidekick-k8s charm change config
  - Blocked the charm is certificates relation does not exist

### Removed

- Health check for falcosidekick
  - This has been proven to be very flaky

## 2026-01-10

Add integration between falco-operator and falcosidekick-k8s-operator via http_endpoint interface.

### Added

- Add http_endpoint interface to falco-operator
- Add http_endpoint interface to falcosidekick-k8s-operator
- Add relation logic in falco-operator to connect to falcosidekick-k8s-operator

### Changed

- Refactor falcosidekick-k8s-operator to not use `relations.py` module
- Fix terraform module tests and README.md
- Update terraform module to include additional relations

## 2026-01-07

Customize RTD configuration.

### Changed

- Update `docs/conf.py` to customize RTD configuration
- Update `workflows/docs.yaml` to check for markdown files other than `docs`

## 2026-01-06

Update terraform modules.

### Changed

- Update terraform Juju provider to version >= 1.1.1
- Update terraform module for falco-operator
  - Update the channel for the falco-operator to "0.42/stable"
  - Update terraform tests to check for expected outputs
  - Update README.md for falco-operator terraform module
- Update terraform module for falcosidekick-k8s-operator
  - Update the channel for the falcosidekick-k8s-operator to "2/stable"
  - Update terraform tests to check for expected outputs
  - Update README.md for falcosidekick-k8s-operator terraform module

## 2026-01-05

Add documentation workflows and RTD set up.

## 2025-12-29

Add integration between falcosidekick-k8s-operator and loki-k8s-operator.

### Added

- Add relation between falcosidekick-k8s-operator and loki-k8s-operator for log forwarding.

## 2025-12-22

Add port configuration option for falcosidekick-k8s-operator.

### Added

- Add `port` configuration option to falcosidekick-k8s-operator

### Changed

- Update charm logic to support configurable listen port

## 2025-12-10

Add `./falcosidekick-k8s-operator` to the monorepo.

### Added

- Add falcosidekick rock image definition to monorepo.
- Add falcosidekick-k8s-operator to monorepo.

### Changed

- Update CI workflows to support `./falcosidekick-k8s-operator` directory.

## 2025-12-10

Migrate the repository to a monorepo structure.

## 2025-12-05

Add configuration for falco.

### Added

- Config option for falco operator that allows setting custom falco configuration
- Unit tests for operator functionality

## 2025-12-04

Create initial version of Falco operator.

### Added

- Initial version of Falco operator implementation
- Unit test functional test for the Falco operator
- Build and release workflow for Falco binary used in this charm
- Renovate configuration for Falco dependency management
- Updated `RELEASE.md` documentation

## 2025-11-25

Set up initial Falco operator project.

### Changed

- Updated `charmcraft.yaml` with Falco-specific configuration
- Updated `README.md` with minimal Falco operator information
- Updated `CONTRIBUTING.md` with minimal documentation
- Updated Python dependencies in `pyproject.toml` and `uv.lock`
- Clean up charm implementation from the template
- Clean up docs content from initial template placeholder
