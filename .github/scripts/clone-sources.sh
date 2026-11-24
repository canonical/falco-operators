#!/usr/bin/env bash
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

set -euo pipefail

required_variables=(
    FALCO_VERSION
    FALCO_GIT_REPO
    FALCO_SOURCE
    FALCO_JSON_PLUGIN_VERSION
    FALCO_K8SAUDIT_PLUGIN_VERSION
    FALCO_PLUGINS_GIT_REPO
    FALCO_PLUGINS_SOURCE
    FALCOCTL_VERSION
    FALCOCTL_GIT_REPO
    FALCOCTL_SOURCE
)

for variable in "${required_variables[@]}"; do
    if [[ -z "${!variable:-}" ]]; then
        echo "Missing required environment variable: $variable" >&2
        exit 1
    fi
done

for directory in "$FALCO_SOURCE" "$FALCO_PLUGINS_SOURCE" "$FALCOCTL_SOURCE"; do
    if [[ "$directory" == "/" ]]; then
        echo "Refusing to remove root directory" >&2
        exit 1
    fi
    rm -rf -- "${directory:?}"
done

mkdir -p "$(dirname "$FALCO_SOURCE")" "$FALCO_PLUGINS_SOURCE" "$(dirname "$FALCOCTL_SOURCE")"

git clone \
    --depth 1 \
    --recurse-submodule \
    --branch "$FALCO_VERSION" \
    "$FALCO_GIT_REPO" \
    "$FALCO_SOURCE"
echo "Falco source cloned at $FALCO_SOURCE with tag: $FALCO_VERSION"

git clone \
    --depth 1 \
    --branch "plugins/json/v$FALCO_JSON_PLUGIN_VERSION" \
    "$FALCO_PLUGINS_GIT_REPO" \
    "$FALCO_PLUGINS_SOURCE/json"
echo "Plugins source cloned at $FALCO_PLUGINS_SOURCE/json with tag: plugins/json/v$FALCO_JSON_PLUGIN_VERSION"

git clone \
    --depth 1 \
    --branch "plugins/k8saudit/v$FALCO_K8SAUDIT_PLUGIN_VERSION" \
    "$FALCO_PLUGINS_GIT_REPO" \
    "$FALCO_PLUGINS_SOURCE/k8saudit"
echo "Plugins source cloned at $FALCO_PLUGINS_SOURCE/k8saudit with tag: plugins/k8saudit/v$FALCO_K8SAUDIT_PLUGIN_VERSION"

git clone \
    --depth 1 \
    --branch "v$FALCOCTL_VERSION" \
    "$FALCOCTL_GIT_REPO" \
    "$FALCOCTL_SOURCE"
echo "falcoctl source cloned at $FALCOCTL_SOURCE with tag: v$FALCOCTL_VERSION"
