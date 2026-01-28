(troubleshoot)=

# Troubleshoot

This guide provides solutions to common issues you may encounter when operating the Falco charms.

## SSH authentication failures

If Falco cannot access a custom configuration repository:

1. Verify the SSH key is correctly added to the Git repository
2. Check the repository URL format is correct (must start with `git+ssh://`)
3. Ensure the username in the URL matches your Git provider (usually `git` for GitHub/GitLab providers)
4. Test SSH access manually: `ssh -T git@github.com` (adjust for your provider)

## Custom rules not loading

If custom rules from a Git repository are not being applied:

1. Verify the repository structure has `rules.d/` and `config.override.d/` directories
2. Check that YAML files in these directories are valid Falco configuration
3. Review Falco logs for syntax errors: `juju ssh falco/0 -- sudo journalctl -u falco -n 100`
4. Verify the repository was cloned: `juju ssh falco/0 -- ls -la /root/custom-falco-config-repository`

## Falco service not starting

If the Falco service fails to start:

1. Check the unit status: `juju status falco`
2. Review service logs: `juju ssh falco/0 -- sudo journalctl -u falco -n 100`
3. Verify kernel module dependencies are met
4. Check configuration file syntax

## Falcosidekick not receiving alerts

If Falcosidekick is not receiving alerts from Falco:

1. Verify the `http-endpoint` relation is established: `juju status --relations`
2. Check Falco is sending alerts: `juju ssh falco/0 -- sudo journalctl -u falco`
3. Check Falcosidekick logs: `juju debug-log --include=falcosidekick-k8s`
4. Verify network connectivity between Falco and Falcosidekick

## Alerts not appearing in Loki

If alerts are not reaching Loki:

1. Verify all integration statuses: `juju status --relations`
2. Check Falcosidekick logs: `juju debug-log --include=falcosidekick-k8s`
3. Check OpenTelemetry Collector logs: `juju debug-log --include=opentelemetry-collector-k8s`
4. Ensure the Loki service is running: `juju status -m cos loki`
5. Verify cross-model integration is working: `juju consumed-offers`

## TLS certificate issues

If you encounter TLS certificate problems:

1. Check certificate status: `juju status --relations`
2. Verify certificate charm logs: `juju debug-log --include=self-signed-certificates` or `juju debug-log --include=lego`
3. Check certificate files are present in the Falcosidekick container
4. For Lego certificates, verify domain DNS is correctly configured

## Connection refused errors

If you see connection refused errors:

1. Verify network connectivity between applications
2. Check that endpoints are accessible
3. Review firewall rules if running in a restricted environment
4. Verify the service is listening on the expected port
