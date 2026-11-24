#!/usr/bin/env bash
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

set -euo pipefail

sudo apt-get update
sudo apt-get install -y \
    build-essential \
    clang \
    cmake \
    git \
    libelf-dev \
    linux-tools-common \
    linux-tools-generic
