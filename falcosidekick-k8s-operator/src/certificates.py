# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm certificates module."""

import logging
from pathlib import Path
from socket import getfqdn
from typing import Optional

import ops
from charmlibs.interfaces.tls_certificates import (
    Certificate,
    CertificateRequestAttributes,
    Mode,
    PrivateKey,
    ProviderCertificate,
    TLSCertificatesRequiresV4,
)

logger = logging.getLogger(__name__)

# See ./templatesfalcosidekick.yaml.j2
KEY = Path("/etc/falcosidekick/certs/server/server.key")
CERT = Path("/etc/falcosidekick/certs/server/server.crt")


class TlsCertificateRequirer:
    """TLS certificate requirer for the charm.

    This class manages the integration with a TLS certificate provider.
    """

    def __init__(self, charm: ops.CharmBase, relation_name: str) -> None:
        """Initialize the TLS certificate requirer.

        Args:
            charm: The charm instance that manages this relation.
            relation_name: The name of the TLS certificate relation endpoint.
        """
        self._charm = charm
        self._relation_name = relation_name
        self._certificates = TLSCertificatesRequiresV4(
            charm=self._charm,
            relationship_name=self._relation_name,
            certificate_requests=[self._get_certificate_request_attributes()],
            mode=Mode.UNIT,
            refresh_events=[self._charm.on.config_changed],
        )

    def is_created(self) -> bool:
        """Check if the TLS certificate relation is created.

        Returns:
            True if the TLS certificate relation is created, False otherwise.
        """
        return bool(self._charm.model.relations.get(self._relation_name))

    def configure(self, container: ops.Container) -> bool:
        """Configure the TLS certificate in the workload container.

        The method retrieves the assigned certificate and private key, checks if they need to be
        updated, and stores them in the container if necessary.

        Args:
            container: The container where the certificates will be configured.

        Returns:
            True if the certificate and key were configured, False otherwise.
        """
        cert, key = self._get_assigned_cert_and_key()
        if not cert or not key:
            logger.warning("Cannot configure TLS: tls_certificate relation not ready")
            return False

        if cert_or_key_updated := self._is_cert_or_key_updated(container, cert.certificate, key):
            logger.info("Updating TLS certificate and private key in workload")
            self._store_file_to_container(container, path=KEY, source=str(key))
            self._store_file_to_container(container, path=CERT, source=str(cert.certificate))

        return cert_or_key_updated

    def _get_assigned_cert_and_key(
        self,
    ) -> tuple[Optional[ProviderCertificate], Optional[PrivateKey]]:
        """Get the currently assigned certificate and private key.

        Returns:
            A tuple containing the assigned certificate and private key, or (None, None) if not
            available.
        """
        if not self.is_created():
            logger.warning("TLS certificate relation not created")
            return None, None

        cert, key = self._certificates.get_assigned_certificate(
            certificate_request=self._get_certificate_request_attributes()
        )
        if not cert or not key:
            logger.warning("Certificate or private key not available")
            return None, None

        return cert, key

    def _get_certificate_request_attributes(self) -> CertificateRequestAttributes:
        """Get the certificate request attributes.

        Returns:
            The attributes for the certificate request.
        """
        sans_ip = set()
        sans_dns = set()

        binding = self._charm.model.get_binding(self._relation_name)
        if binding and binding.network.bind_address:
            sans_ip.add(str(binding.network.bind_address))
        if binding and binding.network.ingress_address:
            sans_ip.add(str(binding.network.ingress_address))

        unit_id = self._charm.unit.name.split("/")[1]
        sans_dns.add(
            f"{self._charm.unit.name.split('/')[0]}-{unit_id}.{self._charm.unit.name.split('/')[0]}-endpoints"
        )

        return CertificateRequestAttributes(
            common_name=getfqdn(),
            sans_ip=sorted(sans_ip),
            sans_dns=sorted(sans_dns),
        )

    def _is_cert_or_key_updated(
        self,
        container: ops.Container,
        certificate: Optional[Certificate],
        private_key: Optional[PrivateKey],
    ) -> bool:
        """Check if the certificate or private key need to be updated.

        Args:
            container: The container where certificates are stored.
            certificate: The new certificate to compare with the existing one.
            private_key: The new private key to compare with the existing one.

        Returns:
            True if the certificate or private key differ from the stored one, False otherwise.
        """
        existing_key = self._get_file_from_container(container, path=KEY)
        existing_cert = self._get_file_from_container(container, path=CERT)
        if not existing_key or not existing_cert:
            return True

        key_changed = PrivateKey.from_string(existing_key) != private_key
        cert_changed = Certificate.from_string(existing_cert) != certificate
        return key_changed or cert_changed

    def _store_file_to_container(self, container: ops.Container, path: Path, source: str) -> None:
        """Store the content to a file in the workload container.

        Args:
            container: The container where the file will be stored.
            path: The path in the container where the file will be stored.
            source: The content to store in the file.
        """
        parent_dir = path.parent
        if not container.isdir(parent_dir):
            container.make_dir(parent_dir, make_parents=True)

        container.push(
            path=path,
            source=source,
        )
        logger.info("Pushed file to workload at %s", path)

    def _get_file_from_container(self, container: ops.Container, path: Path) -> Optional[str]:
        """Retrieve the content of a file from the workload container.

        Args:
            container: The container from which the file will be retrieved.
            path: The path in the container of the file to retrieve.

        Returns:
            The content of the file if it exists, None otherwise.
        """
        if not container.exists(path=path):
            return None
        return str(container.pull(path=path).read())
