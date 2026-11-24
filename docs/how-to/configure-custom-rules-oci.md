(how_to_configure_custom_rules_oci)=

# Configure custom rules from an OCI registry

This guide shows how to configure the Falco charm to fetch custom rules from an OCI registry using
`falcoctl`.

```{note}
OCI rules and Git-based custom configuration are mutually exclusive. Configure only one of
`custom-rules-secret` or `custom-config-repository`. Configuring both puts the unit in a blocked
state.
```

## Prerequisites

- A deployed Falco operator from {ref}`getting started tutorial <tutorial_getting_started>`
- An OCI registry repository containing a Falco rulesfile artifact
- A registry username and password or robot token with read access to the artifact

## Create the secret

Create a Juju secret with the registry credentials and artifact reference. Replace the placeholder
username, password, and OCI reference with your registry values:

```bash
juju add-secret custom-rules-secret username=your-robot password=your-token oci_ref=quay.io/your-org/falco-rules:1.0.0
juju grant-secret custom-rules-secret falco
```

Quote values that contain spaces or shell characters.

The `grant-secret` command returns the secret ID to use in the next step.

## Configure the charm

Set the secret ID returned by `juju grant-secret`. Replace the placeholder ID in the example with
your secret ID:

```bash
juju config falco custom-rules-secret="secret:d5dn431kohtcgpn8ou4g"
```

By default, the charm checks the registry every hour. To change the interval:

```bash
juju config falco custom-rules-follow-interval=6h
```

An empty value uses the default interval of one hour.

## Verify the configuration

Check that the unit is active:

```bash
juju status
```

The `Workload` column for the Falco unit should show `active`:

```text
Unit      Workload  Agent  Machine  Public address  Ports  Message
ubuntu/0* active    idle   0        10.0.0.1
  falco/0* active   idle
```

## Update the rules

Push a new artifact to the registry using the same tag. The follow service checks for updates at the
configured interval and installs changed files directly; Falco reloads automatically. If the new
artifact removes a file, the old file may remain until the next fresh reset.

## Troubleshooting

- The unit is blocked with `Only one of custom-config-repository and custom-rules-secret can be
  configured`: remove one of the two custom rules sources.
- The unit is blocked with `Invalid charm config`: check that the secret contains non-empty
  `username`, `password`, and `oci_ref` keys.
- The unit is blocked with `Failed configuring Falco`: check the registry credentials, the artifact
  reference, and the unit logs for the `falcoctl` error.
- `falcoctl-rules-follow` is not running: check `systemctl status falcoctl-rules-follow` and the
  service logs. The service needs Falco's version endpoint on `127.0.0.1:8765` to be available.
