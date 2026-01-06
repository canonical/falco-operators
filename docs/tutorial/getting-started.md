(tutorial_getting_started)=

# Deploy the Falco charm for the first time

## What you’ll do

- Deploy the Falco charm.
- Deploy any principal charm (e.g. a Ubuntu charm).
- Integrate Falco charm with the principal charm.

## Requirements

You will need a working station, e.g., a laptop, with AMD64 architecture. Your working station
should have at least 4 CPU cores, 8 GB of RAM, and 50 GB of disk space.

> Tip: You can use Multipass to create an isolated environment by running:

> ```
> multipass launch 24.04 --name charm-tutorial-vm --cpus 4 --memory 8G --disk 50G
> ```

> When using a Multipass VM, make sure to replace IP addresses with the
> VM IP in steps that assume you're running locally. To get the IP address of the
> Multipass instance run ```multipass info charm-tutorial-vm```.

This tutorial requires the following software to be installed on your working station
(either locally or in the Multipass VM):

- Juju 3
- LXD 5.21.4

Use [Concierge](https://github.com/canonical/concierge) to set up Juju and LXD:

```bash
sudo snap install --classic concierge
sudo concierge prepare -p machine
```

This first command installs Concierge, and the second command uses Concierge to install
and configure Juju and LXD.

For this tutorial, Juju must be bootstrapped to a LXD controller. Concierge should
complete this step for you, and you can verify by checking for `msg="Bootstrapped Juju" provider=lxd`
in the terminal output and by running `juju controllers`.

If Concierge did not perform the bootstrap, run:

```bash
juju bootstrap lxd tutorial-controller
```

## Set up a tutorial model

To manage resources effectively and to separate this tutorial's workload from
your usual work, create a new model using the following command.

```bash
juju add-model falco-tutorial
```

## Deploy the Falco charm and Ubuntu charm

Falco is a [subordinate](https://documentation.ubuntu.com/juju/3.6/reference/charm/#subordinate-charm) charm.
It needs to be integrated with a [principal](https://documentation.ubuntu.com/juju/3.6/reference/charm/#principal-charm)
charm to work properly.

### Deploy Falco charm and Ubuntu charm

```bash
juju deploy falco --base ubuntu@24.04
juju deploy ubuntu --base ubuntu@24.04
```

### Integrate Falco charm and Ubuntu charm

```bash
juju integrate falco ubuntu
```

<!--
TODO: fill in the actual content, e.g. juju status
-->

## Clean up the environment

Well done! You've successfully completed the Falco tutorial. To remove the
model environment you created during this tutorial, use the following command.

```bash
juju destroy-model falco-tutorial
```
