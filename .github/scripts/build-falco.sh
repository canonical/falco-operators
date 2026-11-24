#!/usr/bin/env bash
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

set -euo pipefail

: "${FALCO_SOURCE:?FALCO_SOURCE is required}"

cd "$FALCO_SOURCE"
mkdir -p build
cd build

cmake \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_CXX_COMPILER="$(command -v g++)" \
    -DCMAKE_C_COMPILER="$(command -v gcc)" \
    -DCMAKE_VERBOSE_MAKEFILE=On \
    -DUSE_BUNDLED_DEPS=On \
    ..

make -j"$(nproc)" falco

ls -lrh ./userspace/falco ./container_plugin-prefix/
./userspace/falco/falco --version
