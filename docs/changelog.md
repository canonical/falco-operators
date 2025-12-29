# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

Each revision is versioned by the date of the revision.

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
