# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for config module."""

import pytest
from pydantic import ValidationError

from config import CharmConfig


class TestCharmConfig:
    """Test CharmConfig class."""

    def test_init_empty(self):
        """Test initialization with empty values."""
        config = CharmConfig()
        assert config.custom_config_repository is None
        assert config.custom_config_repo_ssh_key is None

    def test_init_with_values(self):
        """Test initialization with values."""
        config = CharmConfig(
            custom_config_repository="git+ssh://github.com/user/repo.git",
        )
        assert str(config.custom_config_repository) == "git+ssh://github.com/user/repo.git"
        assert config.custom_config_repo_ssh_key is None

    def test_init_with_valid_url_with_tag(self):
        """Test initialization with valid URL and tags."""
        config = CharmConfig(
            custom_config_repository="git+ssh://github.com/user/repo.git@main",
        )
        assert str(config.custom_config_repository) == "git+ssh://github.com/user/repo.git@main"
        assert config.custom_config_repo_ssh_key is None

    def test_init_with_invalid_url(self):
        """Test initialization with invalid URL."""
        with pytest.raises(ValidationError):
            CharmConfig(custom_config_repository="not a url at all")
