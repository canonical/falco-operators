#!/usr/bin/env bash
# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

set -euo pipefail

: "${ARTIFACT_ROOT:?ARTIFACT_ROOT is required}"
: "${FALCO_SOURCE:?FALCO_SOURCE is required}"
: "${FALCOCTL_SOURCE:?FALCOCTL_SOURCE is required}"
: "${FALCO_PLUGINS_SOURCE:?FALCO_PLUGINS_SOURCE is required}"

mkdir -p \
    "$ARTIFACT_ROOT/etc/falco/rules.d" \
    "$ARTIFACT_ROOT/etc/falco/default_rules" \
    "$ARTIFACT_ROOT/usr/bin" \
    "$ARTIFACT_ROOT/usr/share/falco/plugins"

cp "$FALCO_SOURCE/rules/falco_rules.yaml" "$ARTIFACT_ROOT/etc/falco/default_rules/"
cp "$FALCO_SOURCE/build/userspace/falco/falco" "$ARTIFACT_ROOT/usr/bin/falco"
cp "$FALCOCTL_SOURCE/falcoctl" "$ARTIFACT_ROOT/usr/bin/falcoctl"
chmod +x "$ARTIFACT_ROOT/usr/bin/falco" "$ARTIFACT_ROOT/usr/bin/falcoctl"
cp "$FALCO_SOURCE/build/container_plugin-prefix/src/container_plugin/libcontainer.so" \
    "$ARTIFACT_ROOT/usr/share/falco/plugins"

cp "$FALCO_PLUGINS_SOURCE/k8saudit/plugins/k8saudit/rules/"*.yaml \
    "$ARTIFACT_ROOT/etc/falco/default_rules"
cp "$FALCO_PLUGINS_SOURCE/json/plugins/json/libjson.so" \
    "$ARTIFACT_ROOT/usr/share/falco/plugins"
cp "$FALCO_PLUGINS_SOURCE/k8saudit/plugins/k8saudit/libk8saudit.so" \
    "$ARTIFACT_ROOT/usr/share/falco/plugins"

"$ARTIFACT_ROOT/usr/bin/falcoctl" version
