# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for unit tests."""

import pytest
from ops import testing


@pytest.fixture
def loki_relation():
    """Fixture for Loki push API relation.

    Returns:
        A testing.Relation configured for loki_push_api interface with mock endpoint data.
    """
    return testing.Relation(
        endpoint="send-loki-logs",
        interface="loki_push_api",
        remote_units_data={0: {"endpoint": '{"url": "http://loki:3100/loki/api/v1/push"}'}},
    )
