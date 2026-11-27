#!/usr/bin/env bash
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

set -euo pipefail

: "${FALCOCTL_SOURCE:?FALCOCTL_SOURCE is required}"
: "${FALCOCTL_VERSION:?FALCOCTL_VERSION is required}"

cd "$FALCOCTL_SOURCE"

commit="$(git rev-parse HEAD)"
build_date="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"

CGO_ENABLED=0 go build -trimpath \
    -ldflags "-s -w \
        -X github.com/falcosecurity/falcoctl/cmd/version.semVersion=${FALCOCTL_VERSION} \
        -X github.com/falcosecurity/falcoctl/cmd/version.gitCommit=${commit} \
        -X github.com/falcosecurity/falcoctl/cmd/version.buildDate=${build_date}" \
    -o falcoctl .

./falcoctl version
ls -lrh ./falcoctl
