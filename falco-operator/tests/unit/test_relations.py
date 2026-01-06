# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for relations module."""

from unittest.mock import MagicMock

import pytest

from relations import HttpOutputRequirer


class TestHttpOutputRequirer:
    """Test HttpOutputRequirer class."""

    @pytest.mark.parametrize(
        "scenario,setup",
        [
            ("no_relations", lambda: ({"http-output": []}, None)),
        ],
    )
    def test_get_http_output_info_returns_none(self, scenario, setup):
        """Test get_http_output_info returns None for various scenarios.

        Arrange: Set up mock charm according to scenario.
        Act: Call get_http_output_info.
        Assert: Verify None is returned.
        """
        mock_charm = MagicMock()
        relations, _ = setup()
        mock_charm.model.relations = relations

        requirer = HttpOutputRequirer(mock_charm, "http-output")
        result = requirer.get_http_output_info()

        assert result is None

    @pytest.mark.parametrize(
        "info,description",
        [
            ({"url": "http://falcosidekick:2801"}, "basic HTTP URL"),
            ({"url": "https://falcosidekick.example.com:2801/events"}, "HTTPS with path"),
        ],
    )
    def test_get_http_output_info_valid_infos(self, info, description):
        """Test get_http_output_info returns valid URLs.

        Arrange: Set up mock charm with relation containing valid URL.
        Act: Call get_http_output_info.
        Assert: Verify HttpOutputDataBag is returned with correct URL.
        """
        mock_charm = MagicMock()
        mock_relation = MagicMock()
        mock_app = MagicMock()
        mock_relation.app = mock_app
        mock_relation.data = {mock_app: info}
        mock_charm.model.relations = {"http-output": [mock_relation]}

        requirer = HttpOutputRequirer(mock_charm, "http-output")
        result = requirer.get_http_output_info()

        assert result is not None
        assert result.url == info["url"]
