(how_to_configure_custom_rules_oci)=

# Configure custom rules from an OCI registry

This guide shows how to configure the Falco charm to fetch custom rules from an OCI registry using
`falcoctl`.

```{note}
OCI rules and Git-based custom configuration are mutually exclusive. Configure only one of
`custom-rules-secret` or `custom-config-repository`.
```

## Prerequisites

- A deployed Falco operator from {ref}`getting started tutorial <tutorial_getting_started>`
- An OCI registry repository containing a Falco rulesfile artifact
- A registry username and password or robot token with read access to the artifact

## Push the rules artifact

Package one or more rule files as a tarball and push it with `falcoctl`:

```bash
tar -czf /tmp/falco-rules.tar.gz -C rules.d .
falcoctl registry push \
  --config /dev/null \
  --type rulesfile \
  --version 1.0.0 \
  quay.io/your-org/falco-rules:1.0.0 \
  /tmp/falco-rules.tar.gz
```

## Create the secret

Create a Juju secret whose `value` key contains a JSON object with the registry credentials and
artifact reference:

```bash
juju add-secret custom-rules-secret value='{"username":"your-robot","password":"your-token","oci_ref":"quay.io/your-org/falco-rules:1.0.0"}'
juju grant-secret custom-rules-secret falco  # returns the secret ID
```

## Configure the charm

```bash
juju config falco custom-rules-secret="secret:d5dn431kohtcgpn8ou4g"
```

The charm downloads the artifact into a staging directory under the Falco charm directory and
atomically copies the rule files into the managed rules directory. It checks the registry again on
subsequent `update-status` hooks and installs the new rules if the artifact content has changed.

## Verify the configuration

```bash
juju status
juju ssh falco/0 -- ls -la /var/lib/juju/agents/unit-falco-0/charm/falco/etc/falco/rules.d
juju ssh falco/0 -- ls -la /var/lib/juju/agents/unit-falco-0/charm/falco/etc/falco/oci-rules
```

The unit should be active, the rules should be present in `rules.d`, and the staging directory
should contain the downloaded artifact state and `falcoctl` configuration.

## Update the rules

Push a new artifact to the registry using the same tag. The next `update-status` hook downloads the
artifact and installs the new rules if the content changed.

## Troubleshooting

- The unit is blocked with `Only one of custom-config-repository and custom-rules-secret can be
  configured`: remove one of the two custom rules sources.
- The unit is blocked with `Invalid charm config`: check that the secret contains a `value` key with
  a valid JSON object and that the object contains `username`, `password`, and `oci_ref`.
- The unit is blocked with `Failed configuring Falco`: check the registry credentials, the artifact
  reference, and the unit logs for the `falcoctl` error.
