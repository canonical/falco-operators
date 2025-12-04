# Falco Binary Release

This guide outlines the process for creating a new Falco binary release for the Falco Operator.

## Overview

This document describes the [build](.github/workflows/build_falco.yaml) and [release](.github/workflows/release_falco.yaml)
process for Falco binary. This Falco binary is used by the Falco Operator, and it includes:

- Falco binary
- Falco k8saudit plugin
- Falco default rules
- Falco k8saudit plugin default rules

## Falco Binary Release Process

### 1. Update Version Information

> [!NOTE]
> This step is typically performed by the renovate bot. Manual updates are only necessary if you are creating a release
> outside of the regular schedule.

Edit the `.versions` file in the repository root to specify the Falco and plugin versions to build. You can find the
latest versions on the respective GitHub releases pages.

References:

- [Falco Releases](https://github.com/falcosecurity/falco/releases)
- [Falco Plugins Releases](https://github.com/falcosecurity/plugins/releases)

### 2. Create a Pull Request

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

### 3. Review Build Artifacts (optional)

Once the PR is created, the `Build Falco Binary` workflow will run automatically:

1. Check the GitHub Actions tab for the workflow run
2. Verify that the build completes successfully
3. Review the build logs for any warnings or errors
4. Download and inspect the artifacts if needed (available for 30 days)

### 4. Merge to Main Branch

After the pull request is reviewed and approved, merge the pull request to the `main` branch.

### 5. Create a GitHub Release

Merging the PR to `main` will trigger the [Create Falco Release](.github/workflows/release_falco.yaml) workflow.

### 6. Verify the Release

After the workflow completes:

1. Navigate to the [Releases page](https://github.com/canonical/falco-operator/releases)
2. Verify the new release appears with the correct version
3. Download and verify the tarball contents (optional):

```bash
# Download the release tarball
wget https://github.com/canonical/falco-operator/releases/download/falco/<tag>/falco-<version>-x86_64.tar.gz

# Extract and verify contents
tar -tzf falco-<version>-x86_64.tar.gz

# Verify binary
tar -xzf falco-<version>-x86_64.tar.gz
./usr/bin/falco --version
```

## Troubleshooting

### Version Compatibility

Ensure compatibility between Falco and plugin versions:
- Check the [Falco documentation](https://falco.org/docs/) for plugin compatibility
- Review the plugin release notes for supported Falco versions

## Additional Resources

- [Falco Releases](https://github.com/falcosecurity/falco/releases)
- [Falco Plugins Releases](https://github.com/falcosecurity/plugins/releases)
