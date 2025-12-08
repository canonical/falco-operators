# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

Each revision is versioned by the date of the revision.

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
