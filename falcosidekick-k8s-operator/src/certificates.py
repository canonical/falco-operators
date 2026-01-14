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
    TLSCertificatesRequiresV4,
)
from charms.certificate_transfer_interface.v1.certificate_transfer import (
    CertificateTransferProvides,
)

logger = logging.getLogger(__name__)


class TlsCertificateRequirer:
    """TLS certificate requirer for the charm.

    This class manages the integration with a TLS certificate provider.
    """

    private_key_name = "/etc/falcosidekick/certs/server/server.key"
    certificate_name = "/etc/falcosidekick/certs/server/server.crt"

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

    def is_ready(self) -> bool:
        """Check if the TLS certificate is ready.

        Returns:
            True if the TLS certificate and private key are available, False otherwise.
        """
        if not self._charm.model.relations.get(self._relation_name):
            logger.warning("TLS certificate relation not created")
            return False

        cert, key = self._certificates.get_assigned_certificate(
            certificate_request=self._get_certificate_request_attributes()
        )
        if not cert or not key:
            logger.warning("Certificate or private key not available")
            return False

        return True

    def configure(self, container: ops.Container) -> bool:
        """Configure the TLS certificate in the workload container.

        This method retrieves the currently assigned certificate and private key associated with
        the charm's TLS relation. It checks whether the certificate or private key has changed
        or needs to be updated. If an update is necessary, the new certificate or private key is
        stored.

        Args:
            container: The container where the certificates will be configured.

        Returns:
            True if the certificate or private key was updated, False otherwise.
        """
        if not self.is_ready():
            logger.warning("Cannot configure TLS: tls_certificate relation not ready")
            return False

        cert, key = self._certificates.get_assigned_certificate(
            certificate_request=self._get_certificate_request_attributes()
        )
        if not cert or not key:
            return False

        if cert_updated := self._is_certificate_updated(container, cert.certificate):
            self._store_certificate(container, certificate=cert.certificate)

        if key_updated := self._is_private_key_updated(container, key):
            self._store_private_key(container, private_key=key)

        return cert_updated or key_updated

    def get_ca_cert(self) -> str:
        """Get the CA certificate.

        Returns:
            The CA certificate content as a string. If not available, returns an empty string.
        """
        if not self.is_ready():
            logger.warning("Cannot get CA cert: tls_certificate relation not ready")
            return ""

        cert, _ = self._certificates.get_assigned_certificate(
            certificate_request=self._get_certificate_request_attributes()
        )
        if not cert:
            logger.warning("CA certificate not available")
            return ""

        return str(cert.ca)

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

    def _is_certificate_updated(
        self, container: ops.Container, certificate: Optional[Certificate]
    ) -> bool:
        """Check if the certificate needs to be updated.

        Args:
            container: The container where certificates are stored.
            certificate: The new certificate to compare with the existing one.

        Returns:
            True if the certificate differs from the stored one, False otherwise.
        """
        return self._get_existing_certificate(container) != certificate

    def _is_private_key_updated(
        self, container: ops.Container, private_key: Optional[PrivateKey]
    ) -> bool:
        """Check if the private key needs to be updated.

        Args:
            container: The container where private keys are stored.
            private_key: The new private key to compare with the existing one.

        Returns:
            True if the private key differs from the stored one, False otherwise.
        """
        return self._get_existing_private_key(container) != private_key

    def _get_existing_certificate(self, container: ops.Container) -> Optional[Certificate]:
        """Get the existing certificate from storage.

        Args:
            container: The container where certificates are stored.

        Returns:
            The stored certificate if available, None otherwise.
        """
        if not container.exists(path=self.certificate_name):
            return None
        return self._get_stored_certificate(container)

    def _get_existing_private_key(self, container: ops.Container) -> Optional[PrivateKey]:
        """Get the existing private key from storage.

        Args:
            container: The container where private keys are stored.

        Returns:
            The stored private key if available, None otherwise.
        """
        if not container.exists(path=self.private_key_name):
            return None
        return self._get_stored_private_key(container)

    def _get_stored_certificate(self, container: ops.Container) -> Certificate:
        """Retrieve the certificate stored in the container.

        Args:
            container: The container where certificates are stored.

        Returns:
            The certificate object loaded from the stored file.
        """
        cert_string = str(container.pull(path=self.certificate_name).read())
        return Certificate.from_string(cert_string)

    def _get_stored_private_key(self, container: ops.Container) -> PrivateKey:
        """Retrieve the private key stored in the container.

        Args:
            container: The container where private keys are stored.

        Returns:
            The private key object loaded from the stored file.
        """
        key_string = str(container.pull(path=self.private_key_name).read())
        return PrivateKey.from_string(key_string)

    def _store_certificate(self, container: ops.Container, certificate: Certificate) -> None:
        """Store certificate in the workload container.

        Args:
            container: The container where the certificate will be stored.
            certificate: The certificate to store in the container.
        """
        parent_dir = Path(self.certificate_name).parent
        if not container.isdir(parent_dir):
            container.make_dir(parent_dir, make_parents=True)

        container.push(
            path=self.certificate_name,
            source=str(certificate),
        )
        logger.info("Pushed certificate to workload")

    def _store_private_key(self, container: ops.Container, private_key: PrivateKey) -> None:
        """Store private key in the workload container.

        Args:
            container: The container where the private key will be stored.
            private_key: The private key to store in the container.
        """
        parent_dir = Path(self.private_key_name).parent
        if not container.isdir(parent_dir):
            container.make_dir(parent_dir, make_parents=True)

        container.push(
            path=self.private_key_name,
            source=str(private_key),
        )
        logger.info("Pushed private key to workload")


class CertificateTransferProvider:
    """Certificate transfer provider for the charm.

    This class manages the integration with a certificate transfer interface.
    """

    def __init__(self, charm: ops.CharmBase, relation_name: str) -> None:
        """Initialize the certificate transfer provider.

        Args:
            charm: The charm instance that manages this relation.
            relation_name: The name of the certificate transfer relation endpoint.
        """
        self._charm = charm
        self._relation_name = relation_name
        self._certificate_transfer = CertificateTransferProvides(
            charm=self._charm,
            relationship_name=self._relation_name,
        )

    def configure(self, ca_cert: Optional[str]) -> None:
        """Configure the certificate transfer interface.

        This method transfers or removes the ca_cert depending on its presence. It sends
        the existing CA cert in the workload to relation data bag if ca_cert is present. Otherwise, the CA cert
        is removed from the relation data bag.

        Args:
            ca_cert: The CA certificate to transfer, or None to remove it.
        """
        if not (relations := self._charm.model.relations.get(self._relation_name)):
            logger.warning("Certificate transfer relation not created")
            return

        if not ca_cert:
            for rel in relations:
                self._certificate_transfer.remove_all_certificates(relation_id=rel.id)
                logger.info("Removed CA cert from relation %s", rel.id)
            return

        for rel in relations:
            self._certificate_transfer.add_certificates(certificates={ca_cert}, relation_id=rel.id)
            logger.info("Sent CA certificate to relation %s", rel.id)
