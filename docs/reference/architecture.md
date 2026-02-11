(explanation_architecture)=

# Architecture

This page explains the architecture of the Falco operators and how the components interact to provide runtime security monitoring.

## Overview

The Falco operators consist of two charms that work together to provide comprehensive runtime security monitoring:

- **Falco operator**: A subordinate charm that deploys Falco on machines or Kubernetes nodes
- **Falcosidekick K8s operator**: A Kubernetes charm that receives alerts from Falco and forwards them to various outputs

## Charm deployment architecture

The following diagram shows the complete end-to-end architecture with Falcosidekick, observability, and TLS:

```{mermaid}
graph LR
    subgraph "Falco Deployment Model"
        F[Falco<br/>subordinate charm]
    end

    subgraph "Falcosidekick Model"
        FS[Falcosidekick K8s]
        OT[OpenTelemetry<br/>Collector]

        subgraph "TLS Options"
            SC[Self-signed<br/>Certificates]
            IG[Gateway API<br/>Integrator]
            LG[Lego]
        end
    end

    subgraph "COS Model"
        LK[Loki]
        GF[Grafana]
    end

    F -->|http-endpoint| FS
    FS -->|send-loki-logs| OT
    OT -->|send-loki-logs<br/>cross-model| LK
    LK --> GF

    SC -.->|certificates| FS
    IG -.->|ingress| FS
    LG -.->|certificates| IG

    style F fill:#e1f5ff
    style FS fill:#ffe1e1
    style OT fill:#fff4e1
    style LK fill:#e1ffe1
    style GF fill:#e1ffe1
```

In this architecture:

1. **Alert generation**: Falco detects security events and sends alerts to Falcosidekick through the `http-endpoint` relation
2. **Alert forwarding**: Falcosidekick receives alerts and forwards them to OpenTelemetry Collector using the `send-loki-logs` relation
3. **Log aggregation**: OpenTelemetry Collector sends logs to Loki in the COS model using cross-model relations
4. **Visualization**: Grafana queries Loki to display security alerts in dashboards
5. **TLS termination**: Either self-signed certificates (development) or Gateway API Integrator with Lego (production) provides HTTPS

## Data flow

The following diagram illustrates the data flow from a security event to visualization:

```{mermaid}
sequenceDiagram
    participant Host as Host System
    participant Falco as Falco
    participant FS as Falcosidekick
    participant OT as OpenTelemetry
    participant Loki as Loki
    participant Grafana as Grafana

    Host->>Falco: System call/Kernel event
    Falco->>Falco: Match against rules
    Falco->>FS: Send alert (HTTP/HTTPS)
    FS->>OT: Forward to OpenTelemetry
    OT->>Loki: Push logs (cross-model)
    Grafana->>Loki: Query logs
    Grafana->>Grafana: Display in dashboard
```

## Integration

The charms support the following integration:

### Falco operator

- **`general-info` (requires)**: Attaches to a principal charm to monitor the same host
- **`cos-agent` (provides)**: Exposes metrics and logs for collection by Grafana Agent or OpenTelemetry Collector
- **`http-endpoint` (requires)**: Connects to Falcosidekick to send security alerts

### Falcosidekick K8s operator

- **`certificates` (requires)**: Obtains TLS certificates for HTTPS
- **`grafana-dashboard` (provides)**: Provides pre-configured Grafana dashboards
- **`http-endpoint` (provides)**: Receives alerts from Falco instances
- **`ingress` (requires)**: Exposes the service through an ingress controller
- **`logging` (requires)**: Forwards internal application logs to Loki
- **`metrics-endpoint` (provides)**: Exposes Prometheus metrics for scraping
- **`send-loki-logs` (requires)**: Forwards alerts to OpenTelemetry Collector
