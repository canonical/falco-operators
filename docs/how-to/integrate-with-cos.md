(integrate-with-cos)=

# Integrate Canonical Observability Stack

<!-- vale Canonical.Latinisms = NO -->

This guide shows you how to integrate Falco charms with the Canonical Observability Stack (COS) to
send Falco security alerts to Loki for centralized log aggregation and monitoring.

<!-- vale Canonical.Latinisms = YES -->

## Prerequisites

- A deployed Falco operator from {ref}`deploy Falco tutorial <tutorial_getting_started>`
- A deployed Falcosidekick K8s operator from {ref}`deploy Falcosidekick tutorial <tutorial_deploy_falcosidekick>`

<!-- vale Canonical.007-Headings-sentence-case = NO -->

## Deploy COS Lite

<!-- vale Canonical.007-Headings-sentence-case = YES -->

Deploy [COS Lite](https://github.com/canonical/cos-lite-bundle), which includes Loki, Grafana, Prometheus, and other
observability components.

1. Switch to the controller where you want to deploy COS Lite:

   ```bash
   juju switch k8s-controller
   ```

2. Follow the [official documentation](https://documentation.ubuntu.com/observability/track-2/tutorial/installation/cos-lite-canonical-k8s-sandbox/) to deploy COS Lite.

<!-- vale Canonical.007-Headings-sentence-case = NO -->

## Cross model integration with COS Lite

<!-- vale Canonical.007-Headings-sentence-case = YES -->

Integrate the `opentelemetry-collector-k8s` charm with the COS Lite charms across models using the
offers.

1. Switch back to your `falcosidekick-tutorial` model and consume the offers:

   ```bash
   juju switch falcosidekick-tutorial
   juju consume cos.loki-logging
   juju consume cos.grafana-dashboard
   juju consume cos.prometheus-receive-remote-write
   ```

2. Integrate the `opentelemetry-collector-k8s` charm with the offers:

   ```bash
   juju integrate opentelemetry-collector-k8s:send-loki-logs cos.loki-logging
   juju integrate opentelemetry-collector-k8s:grafana-dashboards-provider cos.grafana-dashboard
   juju integrate opentelemetry-collector-k8s:send-remote-write cos.prometheus-receive-remote-write
   ```

Integrate the `opentelemetry-collector` charm with the COS Lite charms across models using the
offers.

1. Switch back to your `falco-tutorial` model and consume the offers:

   ```bash
   juju switch tutorial-controller:admin/falco-tutorial
   juju consume k8s-controller:admin/cos.loki-logging
   juju consume k8s-controller:admin/cos.grafana-dashboard
   juju consume k8s-controller:admin/cos.prometheus-receive-remote-write
   ```

2. Integrate the `opentelemetry-collector` charm with the offers:

   ```bash
   juju integrate opentelemetry-collector:send-loki-logs k8s-controller:admin/cos.loki-logging
   juju integrate opentelemetry-collector:grafana-dashboards-provider k8s-controller:admin/cos.grafana-dashboard
   juju integrate opentelemetry-collector:send-remote-write k8s-controller:admin/cos.prometheus-receive-remote-write
   ```

Verify the integrations are established:

```bash
juju status --relations -m k8s-controller:admin/cos
juju status --relations -m tutorial-controller:ad min/falco-tutorial
juju status --relations -m k8s-controller:admin/falcosidekick-tutorial
```

You should see the all the units in the `cos` model, `falco-tutorial` model, and `falcosidekick-tutorial` model are `active/idle`.

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

## Monitor with Grafana

Once Falcosidekick is connected to Loki through the `opentelemetry-collector-k8s` charm, you can
monitor the security alerts through the Grafana dashboard in your COS deployment. The alerts will
be available in Loki as structured logs that you can query and visualize.
