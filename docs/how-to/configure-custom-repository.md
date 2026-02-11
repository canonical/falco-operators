(how_to_configure_custom_repository)=

# Configure custom repository

This guide shows how to configure the Falco charm with a custom Git repository containing your own Falco rules and configurations.

## Prerequisites

- A deployed Falco operator from {ref}`getting started tutorial <tutorial_getting_started>`
- A Git repository (e.g., GitHub, GitLab) to host your custom Falco configuration files

## Repository structure

Your custom configuration repository must follow this structure:

```
my-falco-config/
├── rules.d/
│   ├── custom-rules.yaml
└── config.override.d/
    └── custom-config.yaml
```

### Sample rule file

Create a file in `rules.d/` directory, for example `custom-rules.yaml`. You can use the [official
rules from Falco](https://github.com/falcosecurity/rules/blob/main/rules/falco_rules.yaml).

### Sample configuration file

Create a file in `config.override.d/` directory, for example `config.override.d/custom-config.yaml`:

```yaml
rules_files:
  - /etc/falco/rules.d

engine:
  modern_ebpf:
    cpus_for_each_buffer: 2
    buf_size_preset: 4
    drop_failed_exit: false

capture:
  enabled: false
  path_prefix: /tmp/falco
  mode: rules
  default_duration: 5000

plugins_hostinfo: true
```

## Generate SSH keys

Generate an SSH key pair for Falco to access the repository:

```bash
ssh-keygen -t rsa -b 4096 -f ~/falco-repo-key -N ""
```

This creates two files:

- `~/falco-repo-key` - Private key (keep secure)
- `~/falco-repo-key.pub` - Public key (add to your Git repository)

Add the public key to your Git repository's deploy keys or your user account's SSH keys.

## Configure the Falco charm

Set the custom configuration repository using the charm configuration:

```bash
juju config falco custom-config-repository=git+ssh://git@github.com/your-org/your-falco-config.git
juju add-secret custom-config-repo-ssh-key value="$(cat ~/falco-repo-key)"

juju grant-secret custom-config-repo-ssh-key falco  # should return a secret id
juju config falco custom-config-repository-ssh-key="secret:d5dn431kohtcgpn8ou4g"  # use the secret id returned above
```

## Verify the configuration

Check that Falco has loaded your custom configuration:

```bash
juju ssh falco/0 -- ls -la /var/lib/juju/agents/unit-falco-0/charm/falco/etc/falco/rules.d
juju ssh falco/0 -- ls -la /var/lib/juju/agents/unit-falco-0/charm/falco/etc/falco/config.override.d
```

You should see your custom rules files listed in the output.

## Update custom configuration

To update your custom configuration, push changes to your Git repository and update the
configuration. It's a good practice to use a commit hash to specify the exact version of the
repository to use.

Or trigger a configuration update by setting the repository reference:

```bash
juju config falco custom-config-repository=git+ssh://git@github.com/your-org/your-falco-config.git@35e03c8d07636155f78200268928a04a58692c69
```

Falco will automatically sync the changes from the repository.

## Troubleshooting

For troubleshooting common issues with custom repositories, see {ref}`how to troubleshoot <troubleshoot>`.
