# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm config option module."""

from typing import Optional

from ops import Secret
from pydantic import AnyUrl, BaseModel, ConfigDict


class CharmConfig(BaseModel):
    """The pydantic model for charm config.

    Note that the charm config should be loaded via ops.CharmBase.load_config().

    Attributes:
        custom_config_ssh_key (Secret): Optional SSH key for custom configuration repository.
        custom_config_repository (AnyUrl): Optional URL to a custom configuration repository.
    """

    # Pydantic model config
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Charm Configs
    custom_config_repository: Optional[AnyUrl] = None
    custom_config_repo_ssh_key: Optional[Secret] = None
