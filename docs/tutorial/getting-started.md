(tutorial_getting_started)=

# Deploy Falco operator

## What you'll do

- Deploy the K8s charm as the principal charm.
- Deploy the Falco charm to monitor Kubernetes nodes.
- Deploy the Opentelemetry Collector charm to collect and forward Falco metrics.
- Integrate Falco with K8s to enable security monitoring.
- Integrate Falco with Opentelemetry Collector to forward metrics.
- Integrate Opentelemetry Collector with K8s for enhanced observability.
- Verify that Falco is detecting security events on Kubernetes nodes.

## Requirements

You will need a working Canonical Kubernetes cluster. For this tutorial, you can use:

- A production Kubernetes cluster
- A development single node Kubernetes cluster
- Minimum resources: 8 CPU cores, 16 GB RAM, and 150G disk space for each node

````{tip}
You can use Multipass to create an isolated environment by running:

```
multipass launch 24.04 --name charm-tutorial-vm --cpus 8 --memory 16G --disk 150G
```

When using a Multipass VM, make sure to replace IP addresses with the
VM IP in steps that assume you're running locally. To get the IP address of the
Multipass instance run `multipass info charm-tutorial-vm`.
````

This tutorial requires the following software:

- Juju 3

Use [Concierge](https://github.com/canonical/concierge) to set up Juju:

```bash
sudo snap install --classic concierge
sudo concierge prepare -p machine
```

This installs Concierge and uses it to install and configure Juju with a local LXD cloud.

For this tutorial, Juju must be bootstrapped to a LXD controller. Concierge should
complete this step for you. You can verify by running:

```bash
juju controllers
```

You should see output similar to:

```{terminal}
:output-only:
Controller      Model    User   Access     Cloud/Region         Models  Nodes    HA  Version
concierge-lxd*  testing  admin  superuser  localhost/localhost       2      1  none  3.6.13
```

Delete the default `testing` model that Juju creates, we will create a new model for this tutorial in the next step.

```bash
juju destroy-model testing
```

## Set up a tutorial model

To manage resources effectively and to separate this tutorial's workload from
your usual work, create a new model using the following command.

```bash
juju add-model falco-tutorial
```

## Deploy the charms to monitor Kubernetes nodes

Falco and Opentelemetry Collector are [subordinate](https://documentation.ubuntu.com/juju/3.6/reference/charm/#subordinate-charm)
charms. They need to be integrated with a [principal](https://documentation.ubuntu.com/juju/3.6/reference/charm/#principal-charm)
charm to work properly. In this tutorial, we'll use the K8s charm, which allows Falco to monitor
Kubernetes worker nodes for security events.

### Deploy the charms

```bash
juju deploy falco --base ubuntu@24.04 --channel 0.42/edge
juju deploy opentelemetry-collector --base ubuntu@24.04 --channel 2/stable
juju deploy k8s --channel=1.35/stable --base="ubuntu@24.04" --constraints='cores=4 mem=12G root-disk=100G virt-type=virtual-machine'
```

### Integrate the charms

```bash
juju integrate falco k8s
juju integrate falco opentelemetry-collector
juju integrate opentelemetry-collector k8s
```

These integrations deploy Falco and Opentelemetry Collector as subordinates on the K8s node. The
Falco charm monitors the Kubernetes node for runtime security events, while the Opentelemetry
Collector charm collects metrics from both Falco and the K8s node and forwards them to your
observability stack.

## Verify the deployment

Wait for the deployment to complete. You can monitor the status with:

```bash
juju status --watch 1s
```

Once all units show `active/idle`, you should see output similar to:

```{terminal}
:output-only:

Model           Controller     Cloud/Region         Version  SLA          Timestamp
falco-tutorial  concierge-lxd  localhost/localhost  3.6.13   unsupported  08:30:07Z

App                      Version  Status  Scale  Charm                    Channel       Rev  Exposed  Message
falco                             active      1  falco                                   84  no
k8s                               active      1  k8s                      1.35/stable   156  no       Ready
opentelemetry-collector           active      1  opentelemetry-collector  2/stable      148  no

Unit                          Workload  Agent  Machine  Public address  Ports     Message
k8s/0*                        active    idle   0        10.0.0.10       6443/tcp  Ready
  falco/0*                    active    idle            10.0.0.10                 Falco is running
  opentelemetry-collector/0*  active    idle            10.0.0.10
```

### Verify Falco is running

Verify the Falco service is running:

```bash
juju ssh k8s/0 -- sudo systemctl status falco
```

You should see output indicating that Falco is active and running.

### View Falco logs

Falco continuously monitors for security events. View recent security alerts:

```bash
juju ssh k8s/0 -- sudo journalctl -u falco
```

You should see Falco initialization messages and security event detections. Falco monitors
for various security-relevant events such as:

- Processes spawning shells
- Unexpected network connections
- File modifications in sensitive directories
- Privilege escalations
- Container escapes

### Verify Falco metrics are available

```bash
juju ssh falco/0 -- curl -s http://localhost:8765/metrics  # default port is 8765
```

You should see a list of metrics exposed by Falco prefixed with `falcosecurity_`, such as
`falcosecurity_falco_host_num_cpus_total`. These metrics are collected by the Opentelemetry
Collector and forwarded to your observability stack for monitoring and alerting.

## Prepare Falco rules (optional)

By default, Falco operator does not come with any rules. You can customize rules by creating a
custom Git repository for your Falco rules and configuring the Falco charm to use it. To set a
custom rules repository, use the following command:

```bash
juju config falco custom-config-repository=<your-git-repo-url>
juju add-secret custom-config-repo-ssh-key value=<ssh-key>
juju grant-secret custom-config-repo-ssh-key falco
juju config falco custom-config-repo-ssh-key=<juju-secret-id>
```

Replace `<your-git-repo-url>` with the URL of your git repository containing Falco rules and
`<ssh-key>` with the SSH private key that has access to the repository. After configuring, Falco
will pull the rules from the specified repository and apply them.

```{tip}
You can use the official [Falco rules
repository](https://github.com/falcosecurity/rules/blob/main/rules/falco_rules.yaml) as a starting
point. For more information, see the {ref}`Configure custom repository for Falco rules
<how_to_configure_custom_repository>` guide.
```

## Test Falco detection (optional)

If you use the official Falco rules, you generate a security event that Falco will detect.

```bash
juju exec k8s/0 -- sudo cat /etc/shadow
```

Now check the Falco logs again:

```bash
juju exec k8s/0 -- sudo journalctl -u falco
```

You should see a Falco alert similar to:

```{terminal}
:output-only:

Warning Sensitive file opened for reading by non-trusted program (user=root command=cat /etc/shadow file=/etc/shadow)
```

This demonstrates that Falco is actively monitoring the system and detecting security-relevant events.

## Next steps

Well done! You've successfully completed the Falco tutorial. You can now deploy Falcosidekick to
receive and process Falco alerts (see {ref}`Deploy Falcosidekick K8s operator <tutorial_deploy_falcosidekick>`).

## Clean up the environment

If you do not plan to continue the next tutorial, you can remove the model environment you created
during this tutorial by using the following command.

```bash
juju destroy-model falco-tutorial
```

```{note}
If you plan to continue with the next tutorial, keep this model deployed.
```
