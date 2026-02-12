(tutorial_deploy_falcosidekick)=

<!-- vale Canonical.007-Headings-sentence-case = NO -->

# Deploy Falcosidekick K8s operator

<!-- vale Canonical.007-Headings-sentence-case = YES -->

## What you'll do

- Bootstrap a Juju controller on a Kubernetes cloud.
- Deploy the Falcosidekick K8s operator to the Kubernetes cloud.
- Verify the deployment is ready.
- Understand how Falcosidekick receives and processes Falco alerts.

## Requirements

This is a continuation of the previous tutorial. If you haven't set up the Kubernetes cloud with
Juju, see the {ref}`Deploy Falco operator <tutorial_getting_started>` tutorial for setup instructions.

## Preparing the K8s cluster

Before setting up the K8s controller, you need to configure the `k8s` charm with some required features.

```bash
VIP_START="10.8.0.5"
VIP_END="10.8.0.15"

juju config k8s gateway-enabled=true load-balancer-enabled=true  local-storage-enabled=true load-balancer-l2-mode=true load-balancer-cidrs="$VIP_START-$VIP_END"
```

Wait for the configuration to apply:

```bash
juju status --watch 1s
```

You should see the `k8s` application reach `active/idle` status.

## Bootstrap Juju controller on K8s cloud

Once the `k8s` charm is ready, you can proceed to bootstrap the Juju controller on the K8s cloud.

```bash
mkdir -p ~/.kube
juju run k8s/0 get-kubeconfig | yq -r '.kubeconfig' > ~/.kube/config

EXTERNAL_IP=$(juju show-unit -m concierge-lxd:admin/falco-tutorial k8s/0 | yq -r '.k8s/0.public-address')
juju bootstrap k8s k8s-controller --config controller-service-type=loadbalancer --config controller-external-ips=[$EXTERNAL_IP]
```

When the bootstrap is complete, you should see a new controller listed:

```bash
juju controllers
```

You should see output similar to:

```{terminal}
:output-only:

Controller       Model           User   Access     Cloud/Region         Models  Nodes    HA  Version
concierge-lxd    falco-tutorial  admin  superuser  localhost/localhost       2      1  none  3.6.13
k8s-controller*  -               admin  superuser  k8s                       1      1     -  3.6.13
```

## Set up a tutorial model

Create a new model for this tutorial (or use an existing one):

```bash
juju add-model falcosidekick-tutorial
```

<!-- vale Canonical.007-Headings-sentence-case = NO -->

## Deploy Falcosidekick K8s operator

<!-- vale Canonical.007-Headings-sentence-case = YES -->

Falcosidekick is a daemon that connects Falco to your ecosystem. It receives security
alerts from Falco and can forward them to various outputs such as Loki, Slack, or other
monitoring systems.

Deploy the charm:

```bash
juju deploy falcosidekick-k8s --channel 2/edge
```

## Verify the deployment

Wait for the deployment to complete. Monitor the status with:

```bash
juju status --watch 1s
```

You should see output similar to:

```{terminal}
:output-only:

Model                   Controller      Cloud/Region  Version  SLA          Timestamp
falcosidekick-tutorial  k8s-controller  k8s           3.6.13   unsupported  07:58:49Z

App                       Version  Status   Scale  Charm                     Channel   Rev  Address         Exposed  Message
falcosidekick-k8s                  blocked      1  falcosidekick-k8s         2/edge     16  10.152.183.144  no       Required relations: [send-loki-logs]

Unit                        Workload  Agent       Address     Ports  Message
falcosidekick-k8s/0*        blocked   idle        10.1.0.125         Required relations: [send-loki-logs]
```

## Deploy and integrate with the supporting charms

The charm needs to be integrated with some supporting charms to function properly.

```bash
juju deploy self-signed-certificates --channel=1/stable
juju deploy opentelemetry-collector-k8s --channel=2/stable --trust
juju integrate falcosidekick-k8s self-signed-certificates
juju integrate falcosidekick-k8s:logging opentelemetry-collector-k8s
juju integrate falcosidekick-k8s:send-loki-logs opentelemetry-collector-k8s
```

Wait for the deployment to complete. Monitor the status with:

```bash
juju status --watch 1s
```

You should see the status shown as below once the relations are established:

```{terminal}
:output-only:

Model                   Controller      Cloud/Region  Version  SLA          Timestamp
falcosidekick-tutorial  k8s-controller  k8s           3.6.13   unsupported  08:28:54Z

App                          Version  Status   Scale  Charm                        Channel   Rev  Address         Exposed  Message
falcosidekick-k8s                     active       1  falcosidekick-k8s            2/edge     16  10.152.183.144  no
opentelemetry-collector-k8s  0.130.1  blocked      1  opentelemetry-collector-k8s  2/stable  105  10.152.183.27   no       ['cloud-config']|['send-loki-logs'] for receive-loki-logs
self-signed-certificates              active       1  self-signed-certificates     1/stable  317  10.152.183.239  no

Unit                            Workload  Agent  Address     Ports  Message
falcosidekick-k8s/0*            active    idle   10.1.0.240
opentelemetry-collector-k8s/0*  blocked   idle   10.1.0.57          ['cloud-config']|['send-loki-logs'] for receive-loki-logs
self-signed-certificates/0*     active    idle   10.1.0.182
```

```{note}
The `opentelemetry-collector-k8s` charm shows `blocked` status because it requires additional
relations to function properly. This is expected at this stage.
```

## Verify the deployment

### Verify the configuration

You can verify Falcosidekick is configured correctly by checking the config file inside the unit.

```bash
juju ssh --container falcosidekick falcosidekick-k8s/0  cat /etc/falcosidekick/falcosidekick.yaml
```

You should see output similar to:

```{terminal}
:output-only:

listenport: 2801
listenaddress: "" # ip address to bind falcosidekick to (default: "" meaning all addresses)

tlsserver:
  deploy: true
  keyfile: "/etc/falcosidekick/certs/server/server.key"
  certfile: "/etc/falcosidekick/certs/server/server.crt"
  notlsport: 2810
  notlspaths:
    - "/ping"
    - "/healthz"
    - "/metrics"

loki:
  format: json
  extralabels: "juju_unit,juju_charm,juju_model,juju_model_uuid,juju_application"
  endpoint: "/loki/api/v1/push"
  hostport: "http://opentelemetry-collector-k8s-0.opentelemetry-collector-k8s-endpoints.falcosidekick-tutorial.svc.cluster.local:3500"
```

## Understand the deployment

````{note}
In this tutorial, we used the `self-signed-certificates` charm for TLS certificates. In a production
environment, consider using a trusted certificate authority or a more robust TLS management solution.

You may also need to extract the CA certificate from the `self-signed-certificates` charm, and
put it under the k8s nodes' trusted CA store to ensure secure communication between Falco and
Falcosidekick. To extract the CA certificate and save the CA to the k8s node, you can use the
following command:

```bash
juju show-unit -m k8s-controller:admin/falcosidekick-tutorial falcosidekick-k8s/0 --endpoint certificates | yq '."falcosidekick-k8s/0".relation-info[0].application-data.certificates' | yq '.[0].ca' > ca.crt
juju scp -m concierge-lxd:admin/falco-tutorial ca.crt k8s/0:~/ca.crt
juju ssh -m concierge-lxd:admin/falco-tutorial k8s/0 -- sudo mv ca.crt /usr/local/share/ca-certificates/ca.crt
juju ssh -m concierge-lxd:admin/falco-tutorial k8s/0 -- sudo update-ca-certificates
```

````

Falcosidekick K8s operator provides an HTTPS endpoint that Falco can send alerts to. The charm:

- Listens on a configurable port (default: 2801)
- Serving HTTPS requests using TLS certificates obtained from the self-signed-certificates charm
- Provides the `http-endpoint` relation for integration with Falco
- Can forward alerts to Loki using the `send-loki-logs` relation through `opentelemetry-collector-k8s` charm

## Next steps

Well done! You've successfully completed the Falcosidekick tutorial. You can now integrate it with
Falco to receive security alerts (see {ref}`Connect Falco to Falcosidekick <tutorial_end_to_end>`).

## Clean up the environment

If you do not plan to continue the next tutorial, you can remove the model environment you created
during this tutorial by using the following command.

```bash
juju destroy-model falcosidekick-tutorial
```

```{note}
If you plan to continue with the next tutorial, keep this model deployed.
```
