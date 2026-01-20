# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for library code, not involving charm code."""

from pfe.interfaces import falcosidekick_http_endpoint


def test_version():
    assert isinstance(falcosidekick_http_endpoint.__version__, str)
