(tutorial_end_to_end)=

# Connect Falco to Falcosidekick

## What you'll do

- Configure both Falco and Falcosidekick K8s charms.
- Integrate them using the `http-endpoint` relation.
- Verify that Falco alerts are forwarded to Falcosidekick.
- Trigger a security alert and observe the integration.

## Requirements

This is a continuation of the previous tutorials. If you haven't completed the previous tutorials,
review:

- {ref}`Deploy Falco operator <tutorial_getting_started>`
- {ref}`Deploy Falcosidekick K8s operator <tutorial_deploy_falcosidekick>`

## Current status

If you have completed the previous tutorials, you should have the following deployed:

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

and

```{terminal}
:output-only:

Model                   Controller      Cloud/Region  Version  SLA          Timestamp
falcosidekick-tutorial  k8s-controller  k8s           3.6.13   unsupported  08:30:04Z

App                          Version  Status   Scale  Charm                        Channel   Rev  Address         Exposed  Message
falcosidekick-k8s                     active       1  falcosidekick-k8s            2/edge     16  10.152.183.144  no
opentelemetry-collector-k8s  0.130.1  blocked      1  opentelemetry-collector-k8s  2/stable  105  10.152.183.27   no       ['cloud-config']|['send-loki-logs'] for receive-loki-logs
self-signed-certificates              active       1  self-signed-certificates     1/stable  317  10.152.183.239  no

Unit                            Workload  Agent  Address     Ports  Message
falcosidekick-k8s/0*            active    idle   10.1.0.240
opentelemetry-collector-k8s/0*  blocked   idle   10.1.0.57          ['cloud-config']|['send-loki-logs'] for receive-loki-logs
self-signed-certificates/0*     active    idle   10.1.0.182
```

## Integrate Falco with Falcosidekick

Create the relation between Falco and Falcosidekick using the `http-endpoint` interface:

```bash
juju offer -c k8s-controller falcosidekick-tutorial.falcosidekick-k8s:http-endpoint http-endpoint
juju consume -m concierge-lxd:admin/falco-tutorial  k8s-controller:admin/falcosidekick-tutorial.http-endpoint

juju switch concierge-lxd:admin/falco-tutorial
juju integrate falco http-endpoint
```

This establishes the connection that allows Falco to send security alerts to Falcosidekick.

Verify the relation is established:

```bash
juju status --relations
```

You should see:

```{terminal}
:output-only:

Model           Controller     Cloud/Region         Version  SLA          Timestamp
falco-tutorial  concierge-lxd  localhost/localhost  3.6.13   unsupported  08:39:34Z

SAAS           Status  Store           URL
http-endpoint  active  k8s-controller  admin/falcosidekick-tutorial.http-endpoint

App                      Version  Status  Scale  Charm                    Channel       Rev  Exposed  Message
falco                             active      1  falco                                   84  no
k8s                               active      1  k8s                      1.35/stable   156  no       Ready
opentelemetry-collector           active      1  opentelemetry-collector  2/stable      148  no

Unit                          Workload  Agent  Machine  Public address  Ports     Message
k8s/0*                        active    idle   0        10.0.0.10       6443/tcp  Ready
  falco/0*                    active    idle            10.0.0.10                 Falco is running
  opentelemetry-collector/0*  active    idle            10.0.0.10

Machine  State    Address         Inst id        Base          AZ    Message
0        started  10.0.0.10       juju-c5c489-0  ubuntu@24.04  test  Running

Integration provider         Requirer             Interface                    Type         Message
http-endpoint:http-endpoint  falco:http-endpoint  falcosidekick_http_endpoint  regular
k8s:cluster                  k8s:cluster          k8s-cluster                  peer
k8s:cos-tokens               k8s:cos-tokens       cos-k8s-tokens               peer
k8s:juju-info                falco:general-info   juju-info                    subordinate
k8s:upgrade                  k8s:upgrade          upgrade                      peer
...
```

## Understand the integration

The complete integration flow:

1. **Falco monitors the k8s cluster**: Falco runs as a subordinate on the k8s charm, monitoring kernel events and Kubernetes API activities.

2. **Falco processes events**: When a suspicious activity occurs (like reading `/etc/shadow`), Falco matches it against security rules.

3. **Falco sends alerts**: Matching events generate alerts that are sent to the configured `http-endpoint` (Falcosidekick).

4. **Falcosidekick receives alerts**: Falcosidekick receives alerts on its HTTP endpoint (port 2801) and can forward them to various outputs.

The `falcosidekick_http_endpoint` interface handles the connection details automatically, including:

- Port information
- Endpoint URL configuration

## Next steps

At this point you should have a working Falco and Falcosidekick integration ready for use. If you want to learn more
about how to use Falco and Falcosidekick, please check out the {ref}`how-to guides <how_to>` to enhance your deployment
and to learn more about different use cases.

## Clean up the environment

If you want to remove all deployments, use:

```bash
juju destroy-controller k8s-controller --destroy-all-models --destroy-storage
juju destroy-controller concierge-lxd --destroy-all-models --destroy-storage

concierge restore
```

This removes all deployed charms and Juju controllers on the machine, and restore the machine to its previous state
before the tutorial.
