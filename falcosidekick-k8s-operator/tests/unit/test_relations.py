# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for relations module."""

from unittest.mock import MagicMock, patch

import ops
import pytest

from relations import InvalidLokiRelationError, LokiRelationManager


class TestLokiRelationManager:
    """Test LokiRelationManager class."""

    @patch("relations.LokiPushApiConsumer")
    def test_get_loki_http_url_with_endpoints(self, mock_loki_consumer):
        """Test get_loki_http_url returns first endpoint URL.

        Arrange: Set up mock charm with Loki endpoints.
        Act: Call get_loki_http_url().
        Assert: First endpoint URL is returned.
        """
        mock_charm = MagicMock(spec=ops.CharmBase)
        mock_charm.framework = MagicMock()

        mock_consumer_instance = MagicMock()
        mock_consumer_instance.loki_endpoints = [
            {"url": "http://loki1:3100/loki/api/v1/push"},
            {"url": "http://loki2:3100/loki/api/v1/push"},
        ]
        mock_loki_consumer.return_value = mock_consumer_instance

        manager = LokiRelationManager(mock_charm, "logging")
        url = manager.get_loki_http_url()

        # return the first endpoint URL
        assert str(url) == "http://loki1:3100/loki/api/v1/push"

    @patch("relations.LokiPushApiConsumer")
    def test_get_loki_http_url_no_endpoints(self, mock_loki_consumer):
        """Test get_loki_http_url returns None when no endpoints.

        Arrange: Set up mock charm with no Loki endpoints.
        Act: Call get_loki_http_url().
        Assert: None is returned.
        """
        mock_charm = MagicMock(spec=ops.CharmBase)
        mock_charm.framework = MagicMock()

        mock_consumer_instance = MagicMock()
        mock_consumer_instance.loki_endpoints = []
        mock_loki_consumer.return_value = mock_consumer_instance

        manager = LokiRelationManager(mock_charm, "send-loki-logs")
        url = manager.get_loki_http_url()

        assert url is None

    @patch("relations.LokiPushApiConsumer")
    def test_get_loki_http_url_with_invalid_url(self, mock_loki_consumer):
        """Test get_loki_http_url raises InvalidLokiRelationError for invalid URL.

        Arrange: Set up mock charm with invalid Loki endpoint URL.
        Act: Call get_loki_http_url().
        Assert: InvalidLokiRelationError is raised.
        """
        mock_charm = MagicMock(spec=ops.CharmBase)
        mock_charm.framework = MagicMock()

        # if for some reasons the URL is invalid in the relation data bag
        mock_consumer_instance = MagicMock()
        mock_consumer_instance.loki_endpoints = [
            {"url": "not-a-valid-url"},
        ]
        mock_loki_consumer.return_value = mock_consumer_instance

        manager = LokiRelationManager(mock_charm, "send-loki-logs")

        with pytest.raises(InvalidLokiRelationError):
            manager.get_loki_http_url()
