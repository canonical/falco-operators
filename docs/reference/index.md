---
myst:
  html_meta:
    "description lang=en": "Technical information related to the Falco operators"
---

(reference)=

# Reference

Technical details, a high-level architecture description, and interface definitions for the falco operator charm.

## Charm interfaces

<!--
Themes: configuration options, actions, Juju relations
Justification: technical descriptions of the charm control surfaces and integration interfaces
User journey context: configuration, integration, operation
Juju ecosystem scope: charm-specific, cross-charm
-->

The following pages provide more information about the charm's features,
including actions, configurations, and integrations.

```{toctree}
:maxdepth: 1

actions.md
configurations.md
integrations.md
```

## Runtime and deployment

<!--
Themes: deployment architecture, metrics endpoints, backup requirements
Justification: runtime behavior and deployment characteristics of the Falco charms
User journey context: deployment, monitoring, maintenance
Juju ecosystem scope: charm-specific, cross-charm, cloud-level
-->

Overview of the recommended architecture to follow when using falco and falcosidekick, along with the metric types both charms support.

```{toctree}
:maxdepth: 1

architecture.md
metrics.md
back-up-restore.md
```
