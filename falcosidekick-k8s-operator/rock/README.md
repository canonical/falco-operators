# Rock image for falcosidekick

This directory holds the [Rock][Rock] image definition for falcosidekick.

## Build and test

Please follow the [rockcraft documentation][rockcraft documentation] to set up your environment.

To build the rock image and load it into your local docker daemon, run:

```bash
rockcraft pack
rockcraft.skopeo --insecure-policy copy oci-archive:$(ls falcosidekick*.rock) docker-daemon:falcosidekick:local

# Run the falcosidekick container
docker run --name falcosidekick -d falcosidekick:local
```

To test the falcosidekick container, run:

```bash
docker exec falcosidekick pebble checks
```

and you should see output similar to:

```text
Check   Level  Startup  Status  Successes  Failures  Change
health  alive  enabled  up      4          0/3       1
```

## Clean up

To remove the falcosidekick container, run:

```bash
docker rm -f falcosidekick
```

[Rock]: https://documentation.ubuntu.com/rockcraft/stable/explanation/rocks/#explanation-rocks
[rockcraft documentation]: https://documentation.ubuntu.com/rockcraft/stable/tutorial/hello-world/#setup-your-environment
