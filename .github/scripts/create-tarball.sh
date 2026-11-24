#!/usr/bin/env bash
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

set -euo pipefail

: "${ARTIFACT_ROOT:?ARTIFACT_ROOT is required}"
: "${FALCO_VERSION:?FALCO_VERSION is required}"
: "${ARCH:?ARCH is required}"

output_dir="${OUTPUT_DIR:-$PWD}"
tarball="falco-${FALCO_VERSION}-${ARCH}.tar.gz"

mkdir -p "$output_dir"
rm -f "$ARTIFACT_ROOT/$tarball"

cd "$ARTIFACT_ROOT"
tar -czf "$tarball" -- *

# Ensure both binaries are present in the released tarball.
entries="$(tar -tzf "$tarball")"
printf '%s\n' "$entries" | sort
grep -q '^usr/bin/falco$' <<<"$entries"
grep -q '^usr/bin/falcoctl$' <<<"$entries"

mv "$tarball" "$output_dir/"
echo "Created ${output_dir}/${tarball}"
