# Integrations

Falco supports the following integrations with other charms.

### `general-info`

<!-- vale Canonical.004-Canonical-product-names = NO -->
_Interface_: juju-info
<!-- vale Canonical.004-Canonical-product-names = YES -->
_Supported charms_: any principal charms

Since Falco is a subordinate charm, it needs to be integrated with a principal charm via this interface.

Example `general-info` integrate command:

```
juju integrate falco ubuntu
```
