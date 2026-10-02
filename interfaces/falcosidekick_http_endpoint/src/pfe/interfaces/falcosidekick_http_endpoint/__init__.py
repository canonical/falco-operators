# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""The pfe.interfaces.falcosidekick_http_endpoint package."""

from ._falcosidekick_http_endpoint import (
    HttpEndpointInvalidDataError,
    HttpEndpointProvider,
    HttpEndpointRequirer,
)
from ._version import __version__ as __version__

__all__ = [
    "HttpEndpointInvalidDataError",
    "HttpEndpointProvider",
    "HttpEndpointRequirer",
]
