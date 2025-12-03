# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def falco_base_dir(tmp_path):
    """Create a mock Falco base directory structure."""
    base = tmp_path / "falco"
    base.mkdir()
    (base / "usr/bin").mkdir(parents=True)
    (base / "usr/share/falco/plugins").mkdir(parents=True)
    (base / "etc/falco/default_rules").mkdir(parents=True)
    (base / "usr/bin/falco").touch()
    return base


@pytest.fixture
def mock_charm():
    """Create a mock charm."""
    charm = MagicMock()
    charm.model.name = "test-model"
    charm.model.uuid = "test-uuid"
    charm.app.name = "test-app"
    charm.unit.name = "test-unit/0"
    return charm


@pytest.fixture
def mock_falco_dir():
    """Create a temporary Falco directory structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        falco_dir = Path(tmpdir) / "falco"
        falco_dir.mkdir()
        (falco_dir / "usr/bin").mkdir(parents=True)
        (falco_dir / "usr/share/falco/plugins").mkdir(parents=True)
        (falco_dir / "etc/falco/default_rules").mkdir(parents=True)
        (falco_dir / "usr/bin/falco").touch()
        yield falco_dir


@pytest.fixture
def mock_charm_dir(mock_falco_dir):
    """Mock charm directory containing Falco directory."""
    return mock_falco_dir.parent
