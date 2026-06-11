# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for charm integration tests."""

import typing
from collections.abc import Generator

import jubilant
import pytest
from opcli.models.artifacts_build import ArtifactsGenerated
from opcli.pytest_plugin import build_rock_images


@pytest.fixture(scope="module", name="charm")
def charm_fixture(charm_paths):
    """Get the falcosidekick-k8s charm path from built artifacts."""
    return charm_paths["falcosidekick-k8s"].path


@pytest.fixture(scope="session")
def falcosidekick_image(opcli_artifacts: ArtifactsGenerated, opcli_build_yaml_path) -> str:
    """Get the falcosidekick OCI image reference from built artifacts."""
    images = build_rock_images(opcli_artifacts, opcli_build_yaml_path.parent)
    return images["falcosidekick"]


@pytest.fixture(scope="session", name="juju")
def juju_fixture(request: pytest.FixtureRequest) -> Generator[jubilant.Juju, None, None]:
    """Pytest fixture that wraps :meth:`jubilant.with_model`."""

    def show_debug_log(juju: jubilant.Juju):
        """Show debug log.

        Args:
            juju: the Juju object.
        """
        if request.session.testsfailed:
            log = juju.debug_log(limit=1000)
            print(log, end="")

    use_existing = request.config.getoption("--use-existing", default=False)
    if use_existing:
        juju = jubilant.Juju()
        yield juju
        show_debug_log(juju)
        return

    model = request.config.getoption("--model")
    if model:
        juju = jubilant.Juju(model=model)
        yield juju
        show_debug_log(juju)
        return

    keep_models = typing.cast(bool, request.config.getoption("--keep-models"))
    with jubilant.temp_model(keep=keep_models) as juju:
        juju.wait_timeout = 10 * 60
        yield juju
        show_debug_log(juju)
        return
