#!/usr/bin/env bash
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

set -euo pipefail

versions_file="${VERSIONS_FILE:-.versions}"
if [[ ! -f "$versions_file" ]]; then
    echo "Versions file not found: $versions_file" >&2
    exit 1
fi

# shellcheck source=/dev/null
source "$versions_file"

arch="$(uname -m)"

for variable in \
    FALCO_VERSION \
    FALCOCTL_VERSION \
    FALCO_JSON_PLUGIN_VERSION \
    FALCO_K8SAUDIT_PLUGIN_VERSION; do
    if [[ -z "${!variable:-}" ]]; then
        echo "Missing required version variable '$variable' in $versions_file" >&2
        exit 1
    fi
done

write_output() {
    if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
        printf '%s\n' "$1" >>"$GITHUB_OUTPUT"
    else
        printf '%s\n' "$1"
    fi
}

write_output "arch=${arch}"
write_output "falco_version=${FALCO_VERSION}"
write_output "falcoctl_version=${FALCOCTL_VERSION}"
write_output "json_plugin_version=${FALCO_JSON_PLUGIN_VERSION}"
write_output "k8saudit_plugin_version=${FALCO_K8SAUDIT_PLUGIN_VERSION}"

echo "Build information:"
echo "Architecture: ${arch}"
echo "Building Falco version: ${FALCO_VERSION}"
echo "Building falcoctl version: ${FALCOCTL_VERSION}"
echo "Building Falco json plugin version: ${FALCO_JSON_PLUGIN_VERSION}"
echo "Building Falco k8saudit plugin version: ${FALCO_K8SAUDIT_PLUGIN_VERSION}"
