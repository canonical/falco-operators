---
myst:
  html_meta:
    "description lang=en": "How-to guides covering the entire operations lifecycle of the Falco operators."
---

(how_to)=

# How to

Juju configuration, relations, and lifecycle commands help users customize Falco rules, secure Falcosidekick endpoints and route alerts to observability systems.

## Configuration and integrations

<!--
Themes: custom Falco rules, TLS ingress, observability integrations
Justification: configuring charm behavior and connecting Falco services to related operators
User journey context: configuration, integration
Juju ecosystem scope: charm-specific, cross-charm, model-level
-->

Falco charm ships with a default ruleset, use a custom Git repository to add new rules or override settings. Forwarding Falco alerts to COS requires integrating Falco with Falcosidekick first; see {ref}`Connect Falco to Falcosidekick <tutorial_end_to_end>`.

```{toctree}
:maxdepth: 1

configure-custom-repository.md
configure-tls-ingress.md
Integrate with COS <integrate-with-cos.md>
```

## Operations and maintenance

<!--
Themes: troubleshooting, upgrades, documentation contribution
Justification: maintaining deployed charms and the project documentation
User journey context: maintenance, troubleshooting
Juju ecosystem scope: charm-specific
-->

As part of ongoing maintenance, users may need to resolve blocked states that occur during configuration or integrations. Additionally, performing regular version upgrades ensures the charm meets the latest security and community standards.

```{toctree}
:maxdepth: 1

troubleshoot.md
upgrade.md
contribute.rst
```
