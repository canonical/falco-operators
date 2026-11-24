# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for config module."""

import pytest
from pydantic import ValidationError

from config import CharmConfig, InvalidCharmConfigError


class TestCharmConfig:
    """Test CharmConfig class."""

    def test_init_empty(self):
        """Test initialization with empty values."""
        config = CharmConfig()
        assert config.custom_config_repository is None
        assert config.custom_config_repo_ssh_key is None
        assert config.custom_rules_secret is None
        assert config.custom_rules_follow_interval == "1h"

    def test_init_with_values(self):
        """Test initialization with values."""
        config = CharmConfig(
            custom_config_repository="git+ssh://git@github.com/user/repo.git",
        )
        assert str(config.custom_config_repository) == "git+ssh://git@github.com/user/repo.git"
        assert config.custom_config_repo_ssh_key is None
        assert config.custom_rules_secret is None

    def test_init_with_valid_url_with_tag(self):
        """Test initialization with valid URL and tags."""
        config = CharmConfig(
            custom_config_repository="git+ssh://git@github.com/user/repo.git@main",
        )
        assert (
            str(config.custom_config_repository) == "git+ssh://git@github.com/user/repo.git@main"
        )
        assert config.custom_config_repo_ssh_key is None

    def test_init_with_invalid_url(self):
        """Test initialization with invalid URL."""
        with pytest.raises(ValidationError):
            CharmConfig(custom_config_repository="not a url at all")

    def test_init_with_wrong_schema(self):
        """Test initialization with wrong schema."""
        with pytest.raises(InvalidCharmConfigError):
            CharmConfig(custom_config_repository="https://user@github.com/owner/repo.git")

    def test_init_with_missing_username(self):
        """Test initialization with invalid URL."""
        with pytest.raises(InvalidCharmConfigError):
            CharmConfig(custom_config_repository="git+ssh://github.com/owner/repo.git")

    @pytest.mark.parametrize("interval", ["30s", "5m", "1h", "6h", "1h30m"])
    def test_init_with_valid_follow_interval(self, interval):
        """Test valid Go duration follow intervals."""
        config = CharmConfig(custom_rules_follow_interval=interval)
        assert config.custom_rules_follow_interval == interval

    def test_init_with_empty_follow_interval_uses_default(self):
        """Test that an empty follow interval falls back to the default."""
        config = CharmConfig(custom_rules_follow_interval="")
        assert config.custom_rules_follow_interval == "1h"

    @pytest.mark.parametrize("interval", ["5", "five minutes", "1d", "-1h", "500ms"])
    def test_init_with_invalid_follow_interval(self, interval):
        """Test invalid follow intervals."""
        with pytest.raises(ValidationError):
            CharmConfig(custom_rules_follow_interval=interval)
