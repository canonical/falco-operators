(integrate-with-cos)=

# Integrate Falcosidekick with Canonical Observability Stack

<!-- vale Canonical.Latinisms = NO -->

This guide shows you how to integrate Falcosidekick with the Canonical Observability Stack (COS) to
send Falco security alerts to Loki for centralized log aggregation and monitoring.

<!-- vale Canonical.Latinisms = YES -->

## Prerequisites

- A deployed Falcosidekick K8s operator from {ref}`deploy Falcosidekick tutorial <tutorial_deploy_falcosidekick>`

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

## Cross model integration with Loki

Integrate the `opentelemetry-collector-k8s` charm with the `loki-k8s` charm across models using the
`cos.loki-logging` offer.

1. Switch back to your `falcosidekick-tutorial` model and consume the offer:

   ```bash
   juju switch falcosidekick-tutorial
   juju consume cos.loki-logging
   ```

2. Integrate the `opentelemetry-collector-k8s` charm with the `cos.loki-logging` offer:

   ```bash
   juju integrate opentelemetry-collector-k8s:send-loki-logs cos.loki-logging
   ```

3. Verify the integrations are established:

   ```bash
   juju status --relations
   ```

   You should see the all the units in the `cos` model and `falcosidekick-tutorial` model are `active/idle`.

## Verify alert forwarding (optional)

If you have already set up {ref}`custom repository for Falco <how_to_configure_custom_repository>`, you can
verify that by triggering an alert and checking if it appears in Grafana dashboard.

To access the Grafana dashboard from the `cos` model, run the following commands to retrieve the
URL and admin password:

```bash
juju switch cos
juju run grafana/0 get-admin-password
```

In the Grafana dashboard, navigate to `Explore` and select Loki as the data source. You should see
Falco alerts appearing as log entries.

## Monitor alerts in Grafana

Once Falcosidekick is connected to Loki through the `opentelemetry-collector-k8s` charm, you can
monitor the security alerts through the Grafana dashboard in your COS deployment. The alerts will
be available in Loki as structured logs that you can query and visualize.
