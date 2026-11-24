# Falco and falcoctl binary release

This guide outlines the process for creating a new Falco and falcoctl binary release for the Falco Operator.

## Overview

This document describes the [build](../.github/workflows/build_falco.yaml) and [release](../.github/workflows/release_falco.yaml)
process for the Falco and falcoctl binaries. These binaries are used by the Falco Operator, and the release includes:

- Falco binary
- Falcoctl binary
- Falco k8saudit plugin
- Falco default rules
- Falco k8saudit plugin default rules

## Falco binary release process

### Update version information

> [!NOTE]
> This step is typically performed by the renovate bot. Manual updates are only necessary if you are creating a release
> outside of the regular schedule.

Edit the `.versions` file in the repository root to specify the Falco, falcoctl, and plugin versions to build. You can
find the latest versions on the respective GitHub releases pages.

References:

- [Falco Releases](https://github.com/falcosecurity/falco/releases)
- [Falcoctl Releases](https://github.com/falcosecurity/falcoctl/releases)
- [Falco Plugins Releases](https://github.com/falcosecurity/plugins/releases)

### Create a pull request

> [!NOTE]
> This step is typically performed by the renovate bot. Manual updates are only necessary if you are creating a release
> outside of the regular schedule.

Create a pull request with your version changes:

```bash
git checkout -b chore/update-falco-version
git add .versions
git commit -s -m "chore: update Falco to version X.Y.Z"
git push origin update-falco-version
```

The pull request will trigger a test build to verify the build process completes successfully.

### Review build artifacts (optional)

Once the PR is created, the `Build Falco and falcoctl Binaries` workflow will run automatically:

1. Check the GitHub Actions tab for the workflow run
2. Verify that the build completes successfully
3. Review the build logs for any warnings or errors
4. Download and inspect the artifacts if needed (available for 30 days)

### Merge to main branch

After the pull request is reviewed and approved, merge the pull request to the `main` branch.

### Create a GitHub release

Merging the PR to `main` will trigger the [Create Falco and falcoctl Release](../.github/workflows/release_falco.yaml) workflow.

### Verify the release

After the workflow completes:

1. Navigate to the [Releases page](https://github.com/canonical/falco-operators/releases)
2. Verify the new release appears with the correct version
3. Download and verify the tarball contents (optional):

```bash
# Download the release tarball
wget https://github.com/canonical/falco-operators/releases/download/falco/<tag>/falco-<version>-x86_64.tar.gz

# Extract and verify contents
tar -tzf falco-<version>-x86_64.tar.gz

# Verify binaries
tar -xzf falco-<version>-x86_64.tar.gz
./usr/bin/falco --version
./usr/bin/falcoctl version
```

## Build locally

The build workflow delegates its shell steps to scripts under `.github/scripts/`. To run the full
build locally, install the same build dependencies used by CI and Go, then run:

```bash
./.github/scripts/install-build-dependencies.sh
BUILD_ROOT=/tmp/falco-build OUTPUT_DIR=/tmp/falco-release ./.github/scripts/build-all.sh
```

The individual scripts (`clone-sources.sh`, `build-falco.sh`, `build-falco-plugins.sh`,
`build-falcoctl.sh`, `prepare-artifacts.sh`, and `create-tarball.sh`) can also be run separately
with the environment variables defined in `.github/workflows/build_falco.yaml`.

## Troubleshooting

If you have any issue, please follow the steps below to do the troubleshooting:

### Version compatibility

Ensure compatibility between Falco, falcoctl, and plugin versions:
- Check the [Falco documentation](https://falco.org/docs/) for plugin compatibility
- Review the plugin release notes for supported Falco versions
- Review the [falcoctl release notes](https://github.com/falcosecurity/falcoctl/releases) for changes that may affect rule or plugin distribution

## Additional resources

- [Falco Releases](https://github.com/falcosecurity/falco/releases)
- [Falcoctl Releases](https://github.com/falcosecurity/falcoctl/releases)
- [Falco Plugins Releases](https://github.com/falcosecurity/plugins/releases)
