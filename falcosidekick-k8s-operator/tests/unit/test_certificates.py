# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Unit tests for certificates module."""

from unittest.mock import MagicMock, Mock

import ops
import pytest
from charmlibs.interfaces.tls_certificates import Certificate, PrivateKey

from certificates import TlsCertificateRequirer


class TestTlsCertificateRequirer:
    """Test TlsCertificateRequirer class."""

    def test_is_ready_without_relation(self):
        """Test is_ready returns False when TLS relation is missing.

        Arrange: Set up mock charm without TLS relation.
        Act: Check if TLS certificate is ready.
        Assert: is_ready returns False.
        """
        # Arrange
        mock_charm = MagicMock()
        mock_charm.model.relations.get.return_value = None

        tls_requirer = TlsCertificateRequirer(mock_charm, "certificates")

        # Act
        result = tls_requirer.is_ready()

        # Assert
        assert result is False

    @pytest.mark.parametrize(
        "cert,key,expected_result",
        [
            (MagicMock(spec=Certificate), MagicMock(spec=PrivateKey), True),  # Both available
            (MagicMock(spec=Certificate), None, False),  # Only cert
            (None, MagicMock(spec=PrivateKey), False),  # Only key
            (None, None, False),  # Neither available
        ],
    )
    def test_is_ready_with_relation(
        self, mock_get_assigned_certificate, cert, key, expected_result
    ):
        """Test is_ready returns correct value based on certificate availability.

        Arrange: Set up mock charm with TLS relation and optional certificate.
        Act: Check if TLS certificate is ready.
        Assert: is_ready returns expected result based on certificate availability.
        """
        # Arrange
        mock_charm = MagicMock()
        mock_charm.model.relations.get.return_value = [Mock()]
        mock_get_assigned_certificate.return_value = (cert, key)

        tls_requirer = TlsCertificateRequirer(mock_charm, "certificates")

        # Act
        result = tls_requirer.is_ready()

        # Assert
        assert result is expected_result

    def test_configure_not_ready(self):
        """Test configure returns False when TLS is not ready.

        Arrange: Set up TLS requirer that is not ready.
        Act: Configure TLS certificates.
        Assert: Returns False without configuring.
        """
        # Arrange
        mock_charm = MagicMock()
        mock_charm.model.relations.get.return_value = None
        mock_container = MagicMock(spec=ops.Container)

        tls_requirer = TlsCertificateRequirer(mock_charm, "certificates")

        # Act
        result = tls_requirer.configure(mock_container)

        # Assert
        assert result is False
        mock_container.push.assert_not_called()

    def test_configure_update(self, mock_get_assigned_certificate):
        """Test configure with certificate update.

        Arrange: Set up mock container with TLS requirer and certificate.
        Act: Configure TLS certificates.
        Assert: Certificate configuration is processed.
        """
        # Arrange
        mock_charm = MagicMock()
        mock_charm.model.relations.get.return_value = [Mock()]
        mock_container = MagicMock(spec=ops.Container)
        mock_container.exists.return_value = False  # Simulate no existing cert/key

        tls_requirer = TlsCertificateRequirer(mock_charm, "certificates")

        # Act
        result = tls_requirer.configure(mock_container)

        # Assert - certificate updated
        assert result is True
        assert mock_container.push.call_count == 2  # Ensure push was called for cert and key

    def test_configure_no_change(self, mock_get_assigned_certificate):
        """Test configure with no certificate update.

        Arrange: Set up mock container with existing certificates that match new ones.
        Act: Configure TLS certificates.
        Assert: Returns False and no push operations are performed.
        """
        # Arrange
        from unittest.mock import patch

        mock_charm = MagicMock()
        mock_charm.model.relations.get.return_value = [Mock()]
        mock_container = MagicMock(spec=ops.Container)

        tls_requirer = TlsCertificateRequirer(mock_charm, "certificates")

        # Get the certificate and key that the fixture will return
        cert, key = mock_get_assigned_certificate.return_value

        # Patch the methods that retrieve existing certs to return the same ones
        with (
            patch.object(tls_requirer, "_get_existing_certificate", return_value=cert.certificate),
            patch.object(tls_requirer, "_get_existing_private_key", return_value=key),
        ):
            # Act
            result = tls_requirer.configure(mock_container)

        # Assert - certificate not updated
        assert result is False
        mock_container.push.assert_not_called()
