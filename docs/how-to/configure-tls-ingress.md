(configure-tls-ingress)=

# Configure TLS termination with ingress

This guide shows you how to configure TLS termination for Falcosidekick using the `ingress` interface.

## Prerequisites

- A deployed Falcosidekick K8s operator from {ref}`deploy Falcosidekick K8s tutorial <tutorial_deploy_falcosidekick>`

## Configure ingress

### Deploy the required operator

1. Deploy the `gateway-api-integrator` operator:

   ```bash
   juju deploy gateway-api-integrator --channel=latest/stable --config external-hostname=ingress.internal --config gateway-class=ck-gateway --trust
   ```

2. Remove the integration between `falcosidekick` and `self-signed-certificates` if you followed the previous tutorial:

   ```bash
   juju remove-relation falcosidekick-k8s:certificates self-signed-certificates:certificates
   ```

```{tip}
If you have not install the gateway API CRDs, you can do so by following the
[upstream documentation](https://docs.cilium.io/en/stable/network/servicemesh/gateway-api/gateway-api/#gateway-api-support).
```

### Integrate the operators

1. Integrate `self-signed-certificates` with `gateway-api-integrator` to provide certificates:

   ```bash
   juju integrate self-signed-certificates:certificates gateway-api-integrator:certificates
   ```

2. Integrate `falcosidekick-k8s` with `gateway-api-integrator` to enable ingress:

   ```bash
   juju integrate falcosidekick-k8s:ingress gateway-api-integrator:gateway
   ```

## Alternative to `self-signed-certificates` charm for production

For production deployments, consider using the [`lego`](https://charmhub.io/lego) charm to
automatically obtain and renew TLS certificates from Let's Encrypt using the ACME protocol.
