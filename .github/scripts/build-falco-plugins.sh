#!/usr/bin/env bash
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

set -euo pipefail

: "${FALCO_PLUGINS_SOURCE:?FALCO_PLUGINS_SOURCE is required}"

make -C "$FALCO_PLUGINS_SOURCE/json/plugins/json"
make -C "$FALCO_PLUGINS_SOURCE/k8saudit/plugins/k8saudit"

ls -lrh \
    "$FALCO_PLUGINS_SOURCE/json/plugins/json/libjson.so" \
    "$FALCO_PLUGINS_SOURCE/k8saudit/plugins/k8saudit/libk8saudit.so"
