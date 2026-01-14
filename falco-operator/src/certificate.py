# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm state module."""

import logging
import subprocess
from pathlib import Path

from charms.certificate_transfer_interface.v1.certificate_transfer import (
    CertificateTransferRequires,
)
from ops import CharmBase

logger = logging.getLogger(__name__)

CA_CERT_DIR = Path("/usr/local/share/ca-certificates/")


class CertificateTransferRequirer:
    """Wrapper for CertificateTransferRequires interface."""

    def __init__(self, charm: CharmBase, relation_name: str) -> None:
        """Initialize the CertificateTransferRequirer.

        Args:
            charm: The charm instance.
            relation_name: The name of the certificate_transfer relation.
        """
        self._charm = charm
        self._relation_name = relation_name
        self._certificate_transfer_requirer = CertificateTransferRequires(
            charm, relationship_name=relation_name
        )

    def _write_ca_cert(self, ca_cert: str, file_path: Path) -> None:
        """Write the CA certificates to a file.

        Args:
            ca_cert: A CA certificate.
            file_path: The path to the file where the CA certificates will be written.
        """
        with open(file_path, "w", encoding="utf-8") as cert_file:
            cert_file.write(ca_cert)

    def _remove_ca_cert(self, file_path: Path) -> None:
        """Remove the CA certificate file.

        Args:
            file_path: The path to the file to be removed.
        """
        try:
            file_path.unlink()
        except FileNotFoundError:
            logger.warning("CA certificate file %s not found for removal", file_path)

    def _update_ca_certificates(self) -> None:
        """Update the system CA certificates."""
        # Update the system CA certificates
        try:
            subprocess.run(["/usr/sbin/update-ca-certificates"], check=True)
            logger.info("System CA certificates updated successfully")
        except subprocess.CalledProcessError as e:
            logger.error("Failed to update system CA certificates: %s", e)

    def is_created(self) -> bool:
        """Check if the certificate transfer relation is created.

        Returns:
            True if the relation is created, False otherwise.
        """
        return bool(self._charm.model.relations.get(self._relation_name))

    def get_transferred_ca_cert(self) -> dict[int, set[str]]:
        """Get the transferred CA certificate.

        Returns:
            A dictionary mapping relation IDs to sets of CA certificates. If not available, returns
            an empty dictionary.
        """
        if not (relations := self._charm.model.relations.get(self._relation_name)):
            logger.warning("Certificate transfer relation not created")
            return {}

        # limited to only one relation, see charmcraft.yaml
        relation = relations[0]

        if not self._certificate_transfer_requirer.is_ready(relation=relation):
            logger.warning("Cannot get CA cert: relation %s not ready", relation.id)
            return {}

        return {relation.id: self._certificate_transfer_requirer.get_all_certificates(relation.id)}

    def configure(self, ca_certs: dict[str, set[str]]) -> None:
        """Write or remove the transferred CA certificate and update the system CA certificates.

        Args:
            ca_certs: A dictionary mapping relation IDs to sets of CA certificates.
        """
        identifier = "received-ca-cert"
        if not ca_certs:
            for filename in CA_CERT_DIR.glob(f"{identifier}-*-cert-*.crt"):
                self._remove_ca_cert(filename)
                logger.debug("Removed CA certificate file %s", filename)
        else:
            for rel_id, certs in ca_certs.items():
                for i, cert in enumerate(sorted(certs)):
                    filename = CA_CERT_DIR / f"{identifier}-{rel_id}-cert-{i}.crt"
                    self._write_ca_cert(cert, filename)
                    logger.debug("Wrote CA certificate to %s", filename)
        self._update_ca_certificates()
