# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for config module."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from config import CharmConfig, InvalidCharmConfigError, duration_to_ns


class TestCharmConfig:
    """Test CharmConfig class."""

    def test_init_empty(self):
        """Test initialization with empty values."""
        config = CharmConfig()
        assert config.custom_config_repository is None
        assert config.custom_config_repo_ssh_key is None
        assert config.custom_rules_secret is None
        assert config.custom_rules_refresh_interval == "1h"

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

    @pytest.mark.parametrize("interval", ["5m", "10m", "1h", "6h", "1h30m", "1.5h", "1h2h"])
    def test_init_with_valid_refresh_interval(self, interval):
        """Test valid Go duration refresh intervals."""
        config = CharmConfig(custom_rules_refresh_interval=interval)
        assert config.custom_rules_refresh_interval == interval

    def test_init_with_empty_refresh_interval_fails(self):
        """Test that an explicit empty refresh interval is rejected."""
        with pytest.raises(ValidationError):
            CharmConfig(custom_rules_refresh_interval="")

    @pytest.mark.parametrize(
        "interval", ["5", "five minutes", "1d", "1d2d", "-1h", "500ms", "1h 2m"]
    )
    def test_init_with_invalid_refresh_interval(self, interval):
        """Test invalid refresh interval syntax."""
        with pytest.raises(ValidationError):
            CharmConfig(custom_rules_refresh_interval=interval)

    @pytest.mark.parametrize(
        "interval",
        ["0s", "0m0h", "0.0h", "0.0000000001s", "30s", "4m59s"],
    )
    def test_init_with_too_small_refresh_interval(self, interval):
        """Test that intervals below the five-minute minimum are rejected."""
        with pytest.raises(ValidationError):
            CharmConfig(custom_rules_refresh_interval=interval)

    def test_init_with_too_large_refresh_interval(self):
        """Test that refresh intervals beyond Go's duration range are rejected."""
        with pytest.raises(ValidationError):
            CharmConfig(custom_rules_refresh_interval="999999999999999999999h")


@pytest.mark.parametrize(
    ("duration", "expected_ns"),
    [
        ("1s", Decimal(1_000_000_000)),
        ("1m", Decimal(60_000_000_000)),
        ("1h30m", Decimal(5_400_000_000_000)),
        ("1.5h", Decimal(5_400_000_000_000)),
        ("1h2h", Decimal(10_800_000_000_000)),
    ],
)
def test_duration_to_ns(duration, expected_ns):
    """Convert a Go duration string to nanoseconds."""
    assert duration_to_ns(duration) == expected_ns


@pytest.mark.parametrize(
    "duration", ["", "5", "1d", "1d2d", "-1h", "1h30", "1h 2m", "1h 30m", "1h30mfoo"]
)
def test_duration_to_ns_invalid(duration):
    """Reject invalid Go duration strings."""
    with pytest.raises(ValueError):
        duration_to_ns(duration)
