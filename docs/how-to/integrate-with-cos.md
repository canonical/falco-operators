(integrate-with-cos)=

# Integrate with the Canonical Observability Stack

<!-- vale Canonical.Latinisms = NO -->

This guide shows you how to integrate the Falco charms with the Canonical Observability Stack (COS) to
send Falco security alerts to Loki for centralized log aggregation and monitoring.

<!-- vale Canonical.Latinisms = YES -->

## Prerequisites

- A deployed Falco and Opentelemetry Collector operator in the `concierge-lxd:admin/falco-tutorial` model from {ref}`deploy Falco tutorial <tutorial_getting_started>`.
- A deployed Falcosidekick K8s and Opentelemetry Collector K8s operator in the `k8s-controller:admin/falcosidekick-tutorial` model from {ref}`deploy Falcosidekick tutorial <tutorial_deploy_falcosidekick>`.

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

1. Switch back to your `k8s-controller:admin/falcosidekick-tutorial` model and consume the offers:

   ```bash
   juju switch k8s-controller:admin/falcosidekick-tutorial
   juju consume k8s-controller:admin/cos.loki-logging
   juju consume k8s-controller:admin/cos.grafana-dashboard
   juju consume k8s-controller:admin/cos.prometheus-receive-remote-write
   ```

2. Integrate the `opentelemetry-collector-k8s` charm with the offers:

   ```bash
   juju integrate opentelemetry-collector-k8s:send-loki-logs loki-logging
   juju integrate opentelemetry-collector-k8s:grafana-dashboards-provider grafana-dashboard
   juju integrate opentelemetry-collector-k8s:send-remote-write prometheus-receive-remote-write
   ```

3. Integrate the `opentelemetry-collector-k8s` charm with the `falcosidekick-k8s` charm:

   ```bash
   juju integrate falcosidekick-k8s:send-loki-logs opentelemetry-collector-k8s:receive-loki-logs
   juju integrate falcosidekick-k8s:metrics-endpoint opentelemetry-collector-k8s:metrics-endpoint
   juju integrate falcosidekick-k8s:grafana-dashboard opentelemetry-collector-k8s:grafana-dashboards-consumer
   ```

Integrate the `opentelemetry-collector` charm with the COS Lite charms across models using the
offers.

1. Switch back to your `concierge-lxd:admin/falco-tutorial` model and consume the offers:

   ```bash
   juju switch concierge-lxd:admin/falco-tutorial
   juju consume k8s-controller:admin/cos.loki-logging
   juju consume k8s-controller:admin/cos.grafana-dashboard
   juju consume k8s-controller:admin/cos.prometheus-receive-remote-write
   ```

2. Integrate the `opentelemetry-collector` charm with the offers:

   ```bash
   juju integrate opentelemetry-collector:send-loki-logs loki-logging
   juju integrate opentelemetry-collector:grafana-dashboards-provider grafana-dashboard
   juju integrate opentelemetry-collector:send-remote-write prometheus-receive-remote-write
   ```

Verify the integrations are established:

```bash
juju status --relations -m k8s-controller:admin/cos
juju status --relations -m concierge-lxd:admin/falco-tutorial
juju status --relations -m k8s-controller:admin/falcosidekick-tutorial
```

You should see the all the units in the `cos` model, `falco-tutorial` model, and
`falcosidekick-tutorial` model are `active/idle`. At this point, metrics, logs, and Falco alerts
from Falco and Falcosidekick should be collected by Opentelemetry Collector and forwarded to the
Loki and Prometheus in the `cos` model.

## Verify alert forwarding

If you have already set up {ref}`custom repository for Falco <how_to_configure_custom_repository>`, you can
verify that by triggering an alert and checking if it appears in Grafana dashboard.

To access the Grafana dashboard from the `cos` model, run the following commands to retrieve the
URL and admin password:

```bash
juju switch k8s-controller:admin/cos
juju run grafana/0 get-admin-password
```

In the Grafana dashboard, navigate to `Explore` and select Loki as the data source. You should see
Falco alerts appearing as log entries.

## Visualize with Grafana dashboard

A pre-configured dashboard is available in Grafana. You can visualize the Falco alerts by
navigating to `Dashboards > Falco` in the Grafana dashboard.
