(reference_integrations)=

<!-- vale Canonical.007-Headings-sentence-case = NO -->

# Integrations

<!-- vale Canonical.007-Headings-sentence-case = YES -->

## Falco operator

Falco supports the following integrations with other charms.

### Requires

#### `general-info`

<!-- vale Canonical.004-Canonical-product-names = NO -->

_Interface_: juju-info

<!-- vale Canonical.004-Canonical-product-names = YES -->

_Supported charms_: any principal charms

Since Falco is a subordinate charm, it needs to be integrated with a principal charm with this interface.

Example `general-info` integrate command:

```bash
juju integrate falco ubuntu
```

#### `http-endpoint`

_Interface_: falcosidekick_http_endpoint

_Supported charms_: [falcosidekick-k8s](https://charmhub.io/falcosidekick-k8s)

_Limit_: 1

This integration allows Falco to send security alerts to a Falcosidekick instance through HTTP. Falcosidekick acts as a central hub for routing Falco alerts to various outputs (Loki, Slack, and so on).

When integrated, Falco will automatically configure its HTTP output to point to the Falcosidekick endpoint provided through this relation.

Example `http-endpoint` integrate command:

```bash
juju integrate falco:http-endpoint falcosidekick-k8s:http-endpoint
```

## Falcosidekick K8s operator

Falcosidekick K8s supports the following integrations with other charms.

### Provides

#### `http-endpoint`

_Interface_: falcosidekick_http_endpoint

_Supported charms_: [falco](https://charmhub.io/falco)

This integration provides an HTTP endpoint for receiving Falco security alerts. When integrated with the Falco charm, Falcosidekick will expose its HTTP endpoint, allowing Falco to send alerts directly to it.

Example integrate command:

```bash
juju integrate falcosidekick-k8s:http-endpoint falco:http-endpoint
```

### Requires

#### `send-loki-logs`

_Interface_: loki_push_api

_Supported charms_: [loki-k8s](https://charmhub.io/loki-k8s)

_Limit_: 1

This integration allows Falcosidekick to forward Falco alerts to Loki for centralized logging and analysis. When integrated with Loki, all alerts received by Falcosidekick will be automatically pushed to the Loki instance.

Example integrate command:

```bash
juju integrate falcosidekick-k8s:send-loki-logs loki-k8s:logging
```

```{seealso}
{ref}`How to integrate with COS <integrate-with-cos>`
```

#### `certificates`

_Interface_: tls-certificates

_Supported charms_: [self-signed-certificates](https://charmhub.io/self-signed-certificates), [tls-certificates-operator](https://charmhub.io/tls-certificates-operator)

_Limit_: 1

This integration enables TLS/HTTPS for the Falcosidekick HTTP endpoint. When integrated with a TLS certificate provider, Falcosidekick will automatically configure HTTPS with the provided certificates, securing the communication channel for receiving Falco alerts.

Example integrate command:

```bash
juju integrate falcosidekick-k8s:certificates self-signed-certificates:certificates
```

#### `ingress`

_Interface_: ingress

_Supported charms_: [nginx-ingress-integrator](https://charmhub.io/nginx-ingress-integrator), [traefik-k8s](https://charmhub.io/traefik-k8s), [gateway-api-integrator](https://charmhub.io/gateway-api-integrator)

_Limit_: 1

This integration exposes the Falcosidekick HTTP endpoint through a Kubernetes ingress controller, making it accessible from outside the cluster.

Example integrate command:

```bash
juju integrate falcosidekick-k8s:ingress nginx-ingress-integrator:ingress
```
