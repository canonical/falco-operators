(reference_metrics)=

# Metrics

The Falco operators expose Prometheus-compatible metrics for both the Falco runtime security engine and the Falcosidekick alert-forwarding service.

## Falco operator

The Falco operator provides metrics through the `cos-agent` relation:

- Interface: `cos_agent`
- Metrics path: `/metrics`
- Metrics port: `8765`

Falco also ships a Prometheus alert rule for detecting when the scrape target disappears.

## Falcosidekick K8s operator

The Falcosidekick K8s operator provides metrics through the `metrics-endpoint` relation:

- Interface: `prometheus_scrape`
- Metrics path: `/metrics`

The charm updates the scrape job specification dynamically so that Prometheus-compatible collectors can scrape either the configured Falcosidekick listen port or the non-TLS port, depending on whether ingress is in use:

- Default listen port: `2801`
- Non-TLS metrics port: `2810`

The workload also exposes `/metrics` as a non-TLS path
alongside the health endpoints when TLS is configured.

Falcosidekick also ships a Prometheus alert rule for detecting when
the scrape target disappears.
