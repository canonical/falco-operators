(explanation_charm_design)=

# Charm design overview

This page explains the design patterns and architecture used in both the Falco operator and Falcosidekick K8s operator charms.

## Design philosophy

Both charms follow a consistent design pattern that separates concerns into distinct modules, making the codebase maintainable and testable. The design emphasizes:

- **Single source of truth**: All configuration and relation data is aggregated into a single state object
- **Separation of concerns**: Clear boundaries between charm logic, state management, and workload configuration
- **Declarative configuration**: The workload is configured based on the desired state, not through imperative commands

## Architecture pattern

Both charms implement the same architectural pattern:

```{mermaid}
graph LR
    E[Events] --> H[Observed in charm.py]
    H --> R[Relation Libraries]
    H --> C[Configuration]
    R --> S[State Module]
    C --> S
    S --> W[Workload/Service Module]
    W --> T[Templates]
    W --> WL[Workload/System]

    style S fill:#ffe1e1
    style W fill:#e1f5ff
    style H fill:#fff4e1
```

The flow of data through the charm follows this pattern:

1. **Events trigger handlers**: Juju events (`config-changed`, `relation-changed`) are observed in `charm.py`
2. **Data collection**: Handlers gather data from configuration options and relation libraries
3. **State aggregation**: All data is combined into a single `CharmState` object in the `state.py` module
4. **Workload configuration**: The workload module (`service.py` or `workload.py`) receives the state and configures the service accordingly

## Module responsibilities

### `charm.py`

The main charm module coordinates the overall charm behavior:

- Observes Juju lifecycle events (`install`, `config-changed`, `upgrade`)
- Observes relation events (`relation-joined`, `relation-changed`, `relation-broken`)
- Initializes relation libraries and helper objects
- Delegates workload configuration to the service/workload module

For example, the Falco operator observes the `http-endpoint` and `cos-agent` relations and triggers reconciliation
when they change, while the Falcosidekick K8s operator observes multiple relations including
`send-loki-logs`, `certificates`, `ingress`, `logging`, `grafana-dashboard`, and `metrics-endpoint`.

### `state.py`

The state module provides a single source of truth for all charm data:

- Aggregates charm configuration options
- Collects data from relation libraries
- Validates and transforms data into a consistent format using Pydantic models
- Provides a `CharmState` object that represents the complete desired state

For example, in the Falcosidekick K8s operator, the state module combines:

- Configuration options (port)
- Loki endpoint from the `send-loki-logs` relation
- TLS certificate data from the `certificates` relation
- Ingress configuration from the `ingress` relation

All of this data is validated and packaged into a single `CharmState` object that the workload module can consume.

### `service.py` / `workload.py`

The workload module configures the service based on the charm state:

- Receives the `CharmState` object from the charm
- Renders configuration templates with state data
- Manages the lifecycle of the workload (install, configure, restart)
- Interacts with the workload (systemd service for Falco, Pebble container for Falcosidekick K8s)

For the Falco operator, `service.py` manages:

- Falco configuration files rendered from templates
- Custom configuration from Git repositories
- Systemd service lifecycle

For the Falcosidekick K8s operator, `workload.py` manages:

- Pebble layer configuration
- Container configuration files
- TLS certificate installation
- Health checks

### Relation handlers

Both charms use relation libraries to handle integrations:

- **Falco operator**: Uses `HttpEndpointRequirer` to connect to Falcosidekick and `CosAgentProvider` for metrics collection
- **Falcosidekick K8s operator**: Uses `HttpEndpointProvider`, `LokiPushApiConsumer`, `LogForwarder`, `TlsCertificateRequirer`, `IngressPerAppRequirer`, `GrafanaDashboardProvider`, and `MetricsEndpointProvider`

These libraries abstract the complexity of relation data exchange and provide clean interfaces for the charm to use.

## Configuration flow

The configuration flow in both charms follows this sequence:

```{mermaid}
sequenceDiagram
    participant J as Juju
    participant C as charm.py
    participant S as state.py
    participant W as workload / service module
    participant WL as Workload / Service

    J->>C: Event (config-changed, relation-changed)
    C->>C: Observe event
    C->>S: CharmState.from_charm()
    S->>S: Load config
    S->>S: Gather relation data
    S->>S: Validate and transform
    S->>C: Return CharmState
    C->>W: configure(state)
    W->>W: Render templates
    W->>WL: Apply configuration
    W->>WL: Restart if needed
    WL->>C: Service status
    C->>J: Set unit status
```

This pattern ensures that:

- Configuration is always derived from the current state
- All changes go through the same validation and transformation logic
- The workload is configured holistically rather than incrementally

## Template system

Both charms use Jinja2 templates for configuration files. These templates are stored in the `src/templates/` directory,
and the workload module renders templates with the charm state as context. The rendered files are installed in the
appropriate locations.

For example, the Falco operator uses templates for:

- Falco configuration files
- Systemd service files

The Falcosidekick K8s operator uses templates for:

- Falcosidekick configuration files
- Pebble layer definitions

## Error handling

Both charms implement consistent error handling:

- Configuration validation errors are caught and result in a `BlockedStatus`
- Missing required relations result in a `BlockedStatus` with a clear message
- Runtime errors are logged and reported through the unit status

This ensures that operators have clear visibility into charm state and can take corrective action when needed.
