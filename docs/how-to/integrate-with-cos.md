(integrate-with-cos)=

# Integrate Falcosidekick with Canonical Observability Stack

<!-- vale Canonical.Latinisms = NO -->

This guide shows you how to integrate Falcosidekick with the Canonical Observability Stack (COS) to
send Falco security alerts to Loki for centralized log aggregation and monitoring.

<!-- vale Canonical.Latinisms = YES -->

## Prerequisites

- A deployed Falcosidekick k8s operator from [deploy Falcosidekick tutorial](../tutorial/deploy-falcosidekick)

## Deploy COS lite bundle

Deploy the [COS lite bundle](https://github.com/canonical/cos-lite-bundle), which includes Loki,
Grafana, Prometheus, and other observability components.

0. Switch to the controller where you want to deploy COS:

   ```bash
   juju switch k8s-controller
   ```

1. Create a new model for COS:

   ```bash
   juju add-model cos
   ```

2. Deploy the COS lite bundle with overlays:

   ```bash
   curl -sL https://raw.githubusercontent.com/canonical/cos-lite-bundle/main/overlays/offers-overlay.yaml -O
   curl -sL https://raw.githubusercontent.com/canonical/cos-lite-bundle/main/overlays/storage-small-overlay.yaml -O

   juju deploy cos-lite \
   --trust \
   --overlay ./offers-overlay.yaml \
   --overlay ./storage-small-overlay.yaml
   ```

3. Wait for the deployment to complete:

   ```bash
   juju status --watch 1s
   ```

## Integrate with opentelemetry-collector-k8s

Falcosidekick sends logs to Loki through the opentelemetry-collector-k8s charm, which acts as a log aggregation and forwarding layer.

1. Switch to your Falcosidekick model:

   ```bash
   juju switch falcosidekick-tutorial
   ```

2. Deploy the opentelemetry-collector-k8s charm if not already deployed:

   ```bash
   juju deploy opentelemetry-collector-k8s --channel=2/stable --trust
   ```

3. Integrate Falcosidekick with opentelemetry-collector-k8s: if not already integrated

   ```bash
   juju integrate falcosidekick-k8s:send-loki-logs opentelemetry-collector-k8s:receive-loki-logs
   ```

## Cross model integration with Loki

Integrate the opentelemetry-collector-k8s with Loki across models using offers.

1. Switch back to your Falcosidekick model and consume the offer:

   ```bash
   juju switch falcosidekick-tutorial
   juju consume cos.loki-logging
   ```

2. Integrate opentelemetry-collector-k8s with the Loki offer:

   ```bash
   juju integrate opentelemetry-collector-k8s:send-loki-logs cos.loki-logging
   ```

3. Verify the integrations are established:

   ```bash
   juju status --relations
   ```

   You should see the all the units in the `cos` and `falcosidekick-tutorial` models are `active/idle`.

## Verify alert forwarding

1. Trigger a test Falco alert.

2. Access the Grafana dashboard from the COS model:

   ```bash
   juju switch cos
   juju run grafana/0 get-admin-password
   ```

3. In Grafana, navigate to `Explore` and select Loki as the data source. You should see Falco alerts appearing as log entries.

## Monitor alerts in Grafana

Once Falcosidekick is connected to Loki through `opentelemetry-collector-k8s`, you can monitor the
security alerts through the Grafana dashboard in your COS deployment. The alerts will be available
in Loki as structured logs that you can query and visualize.
