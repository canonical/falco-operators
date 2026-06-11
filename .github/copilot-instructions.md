# Copilot Instructions

## Repository Overview

This is a mono-repo containing two Juju charmed operators and one charm interface for [Falco](https://falco.org/) and [Falcosidekick](https://github.com/falcosecurity/falcosidekick):

- **`falco-operator/`** — Machine (subordinate) charm for Falco runtime security on Ubuntu VMs
- **`falcosidekick-k8s-operator/`** — Kubernetes charm for Falcosidekick (routes Falco alerts to outputs)
- **`interfaces/falcosidekick_http_endpoint/`** — Charm interface library connecting the two operators

Each charm is a self-contained Python project with its own `pyproject.toml`, `tox.toml`, `uv.lock`, and `charmcraft.yaml`.

## Architecture

### Charm pattern

Both charms follow the same structural pattern:

- **`charm.py`** — Entry point. Extends `CharmBaseWithState`, registers event observers, delegates all logic to the `reconcile()` method on every relevant event.
- **`state.py`** — Pydantic `CharmState` model built via `CharmState.from_charm(...)`. Reads config, relation data, and secrets; raises typed exceptions on invalid input.
- **`config.py`** — Pydantic model for charm config validation; used by `state.py` via `charm.load_config(CharmConfig)`.
- **`workload.py`** (k8s charm) / **`service.py`** (machine charm) — All workload logic: configuring, starting/stopping, and health-checking the service.

The `CharmBaseWithState` ABC in `state.py` enforces that every charm exposes a `state` property and a `reconcile` method.

### Interface library

`interfaces/falcosidekick_http_endpoint/` is a local Python package (`pfe-interfaces-falcosidekick-http-endpoint`) referenced via `uv.sources` in both charms' `pyproject.toml`. Imported as `from pfe.interfaces.falcosidekick_http_endpoint import ...`.

### Falco binary packaging

The Falco binary is not installed from the Ubuntu package manager — it is downloaded as a custom-built tarball from GitHub Releases during `charmcraft pack` (see the `falco` part in `falco-operator/charmcraft.yaml`). The version is managed by Renovate via the comment `# renovate: depName=canonical/falco-operators`.

## Build, Test, and Lint

All commands below must be run from within the specific charm directory (e.g., `falco-operator/` or `falcosidekick-k8s-operator/`), not the repo root.

### Setup

```bash
uv python install
uv tool install tox --with tox-uv
uv sync --all-groups
source .venv/bin/activate
```

### Run all checks

```bash
tox
```

### Individual environments

```bash
tox -e fmt        # Auto-fix formatting with ruff
tox -e lint       # codespell + ruff + mypy
tox -e static     # bandit security analysis
tox -e unit       # Unit tests with coverage
tox -e integration # Integration tests (requires Juju)
```

### Run a single unit test

```bash
tox -e unit -- tests/unit/test_charm.py::TestClassName::test_method_name
```

Posargs are passed directly to `pytest`, so any pytest flags work (e.g., `-k`, `-x`).

### Build a charm

```bash
charmcraft pack
```

### Documentation

From the repo root:

```bash
make docs-check   # Validate markdown changes
```

From the `docs/` directory:

```bash
make spelling
make linkcheck
make vale
make lint-md
make run          # Local preview
```

## Key Conventions

### Reconciliation pattern

The charm does not have separate handlers per event type. All events that can affect configuration call `self.reconcile(_)`. State is lazy-loaded and cached: `self._state = None` is reset each reconcile cycle. Do not add per-event-type logic in `charm.py`; put it in `workload.py` / `service.py` instead.

### Pydantic for config and state

Config validation uses Pydantic v2 via `charm.load_config(CharmConfig)`. The `CharmState.from_charm()` classmethod is the single place that assembles all runtime state from config, relation data, and secrets. Raise `InvalidCharmConfigError` for config problems and relation-specific exceptions (e.g., `RequireOneOfIngressOrCertificateRelationError`) for relation problems. Never raise generic exceptions for expected error conditions.

### Charm libraries (lib/)

Third-party charm libraries (e.g., `grafana_agent.cos_agent`, `loki_k8s.loki_push_api`) are vendored into `lib/charms/`. They are declared in `charmcraft.yaml` under `charm-libs` and fetched with `charmcraft fetch-libs`. Do not modify these files directly.

### Interface library (pfe)

The `pfe-interfaces-falcosidekick-http-endpoint` package is the local interface library at `interfaces/falcosidekick_http_endpoint/`. Changes to the interface must be reflected in both charms' `uv.lock` (run `uv sync` in each charm directory after modifying the interface).

### Ruff line length and docstring style

Line length is 99 characters. Docstrings follow the Google convention (`pydocstyle.convention = "google"`). Docstrings are required for all public symbols except `__init__` (D107 is suppressed). Test files are exempt from docstring rules.

### Copyright header

Every source file must begin with:

```python
# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
```

Enforced by `ruff` rule `CPY` with `lint.flake8-copyright.notice-rgx`.

### Changelog

Add an entry to `docs/changelog.md` for every new feature, fix, or significant change. Use the contribution date as the header.

### Commits

All commits must be signed (GPG/SSH verified signatures required). Include the Canonical CLA sign-off line at the end of the commit message.
