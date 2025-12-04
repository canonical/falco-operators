# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""Fixtures for charm tests."""


def pytest_addoption(parser):
    """Parse additional pytest options.

    Args:
        parser: Pytest parser.
    """
    parser.addoption("--charm-file", action="store")
    parser.addoption(
        "--keep-models",
        action="store_true",
        default=False,
        help="Keep temporarily-created models",
    )
    parser.addoption(
        "--use-existing",
        action="store_true",
        default=False,
        help="Use existing models and not created models",
    )
    parser.addoption(
        "--model",
        action="store",
        help="Temporarily-created model name",
    )
    parser.addoption(
        "--base",
        action="store",
        default="ubuntu@24.04",
        help="Ubuntu base to deploy the charm on",
    )
