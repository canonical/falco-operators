(changelog)=

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

Each revision is versioned by the date of the revision.

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
