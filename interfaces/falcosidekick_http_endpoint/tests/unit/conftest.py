# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for unit tests, typically mocking out parts of the external system."""

import typing
from typing import Any

import ops
import ops.testing
import pytest

from pfe.interfaces.falcosidekick_http_endpoint._falcosidekick_http_endpoint import (
    HttpEndpointProvider,
    HttpEndpointRequirer,
)


class ProviderCharm(ops.CharmBase):
    """Test charm for HttpEndpointProvider."""

    def __init__(self, *args: typing.Any):
        super().__init__(*args)
        self.provider = HttpEndpointProvider(self, "falcosidekick-http-endpoint")


class RequirerCharm(ops.CharmBase):
    """Test charm for HttpEndpointRequirer."""

    def __init__(self, *args: typing.Any):
        super().__init__(*args)
        self.requirer = HttpEndpointRequirer(self, "falcosidekick-http-endpoint")


@pytest.fixture
def provider_charm_meta() -> dict[str, Any]:
    """Return the metadata for the ProviderCharm."""
    return {
        "name": "provider-charm",
        "provides": {"falcosidekick-http-endpoint": {"interface": "falcosidekick_http_endpoint"}},
    }


@pytest.fixture
def requirer_charm_meta() -> dict[str, Any]:
    """Return the metadata for the RequirerCharm."""
    return {
        "name": "requirer-charm",
        "requires": {"falcosidekick-http-endpoint": {"interface": "falcosidekick_http_endpoint"}},
    }


@pytest.fixture
def requirer_charm_relation_1() -> ops.testing.Relation:
    """Return a relation for the RequirerCharm."""
    return ops.testing.Relation(
        endpoint="falcosidekick-http-endpoint",
        interface="falcosidekick_http_endpoint",
        remote_app_name="remote_1",
        remote_app_data={
            "url": '"http://10.0.0.1:8080/"',
        },
    )


@pytest.fixture
def requirer_charm_relation_2() -> ops.testing.Relation:
    """Return a relation for the RequirerCharm."""
    return ops.testing.Relation(
        endpoint="falcosidekick-http-endpoint",
        interface="falcosidekick_http_endpoint",
        remote_app_name="remote_2",
        remote_app_data={
            "url": '"https://10.0.1.1:8443/"',
        },
    )


@pytest.fixture
def provider_charm_relation_1() -> ops.testing.Relation:
    """Return a relation for the ProviderCharm."""
    return ops.testing.Relation(
        endpoint="falcosidekick-http-endpoint",
        interface="falcosidekick_http_endpoint",
    )


@pytest.fixture
def provider_charm_relation_2() -> ops.testing.Relation:
    """Return a relation for the ProviderCharm."""
    return ops.testing.Relation(
        endpoint="falcosidekick-http-endpoint",
        interface="falcosidekick_http_endpoint",
    )
