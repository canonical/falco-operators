#!/usr/bin/env bash
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/../.." && pwd)"
versions_file="${VERSIONS_FILE:-${repo_root}/.versions}"

# shellcheck source=/dev/null
source "$versions_file"
export FALCO_VERSION FALCOCTL_VERSION FALCO_JSON_PLUGIN_VERSION FALCO_K8SAUDIT_PLUGIN_VERSION

build_root="${BUILD_ROOT:-/tmp/falco-build}"
export FALCO_SOURCE="${FALCO_SOURCE:-${build_root}/falco}"
export FALCO_PLUGINS_SOURCE="${FALCO_PLUGINS_SOURCE:-${build_root}/plugins}"
export FALCOCTL_SOURCE="${FALCOCTL_SOURCE:-${build_root}/falcoctl}"
export ARTIFACT_ROOT="${ARTIFACT_ROOT:-${build_root}/artifacts}"
export OUTPUT_DIR="${OUTPUT_DIR:-${repo_root}}"
export ARCH="${ARCH:-$(uname -m)}"
export FALCO_GIT_REPO="${FALCO_GIT_REPO:-https://github.com/falcosecurity/falco.git}"
export FALCO_PLUGINS_GIT_REPO="${FALCO_PLUGINS_GIT_REPO:-https://github.com/falcosecurity/plugins.git}"
export FALCOCTL_GIT_REPO="${FALCOCTL_GIT_REPO:-https://github.com/falcosecurity/falcoctl.git}"

"$script_dir/extract-versions.sh" >/dev/null
"$script_dir/clone-sources.sh"
"$script_dir/build-falco.sh"
"$script_dir/build-falco-plugins.sh"
"$script_dir/build-falcoctl.sh"
"$script_dir/prepare-artifacts.sh"
"$script_dir/create-tarball.sh"
