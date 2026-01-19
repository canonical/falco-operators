# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for unit tests."""

from unittest.mock import MagicMock, patch

import pytest
from ops import testing

from certificates import PrivateKey, ProviderCertificate


@pytest.fixture
def mock_get_assigned_certificate():
    """Provide a patcher for TLSCertificatesRequiresV4.get_assigned_certificate.

    This fixture returns a context manager that can be configured with different
    return values for each test. By default, it returns valid certificate and key mocks.

    Yields:
        A patch context manager for get_assigned_certificate with default valid cert/key.
    """
    with patch("certificates.TLSCertificatesRequiresV4.get_assigned_certificate") as mock:
        mock_cert = MagicMock(spec=ProviderCertificate, certificate="mock cert")
        mock_key = MagicMock(spec=PrivateKey)
        mock.return_value = (mock_cert, mock_key)
        yield mock


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


@pytest.fixture
def http_endpoint_relation():
    """Fixture for HTTP endpoint relation.

    Returns:
        A testing.Relation configured for http_endpoint interface.
    """
    return testing.Relation(
        endpoint="http-endpoint",
        interface="http_endpoint",
    )


@pytest.fixture
def certificates_relation():
    """Fixture for TLS certificates relation.

    Returns:
        A testing.Relation configured for certificates interface.
    """
    return testing.Relation(
        endpoint="certificates",
        interface="tls_certificates",
    )


@pytest.fixture
def ingress_relation():
    """Fixture for Ingress relation.

    Returns:
        A testing.Relation configured for ingress interface.
    """
    return testing.Relation(
        endpoint="ingress",
        interface="ingress",
    )
