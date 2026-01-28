# Contributing

To make contributions to this interface library, you'll need a working
[development setup](https://documentation.ubuntu.com/juju/latest/user/howto/manage-your-deployment/manage-your-deployment-environment/).

The code for this library can be downloaded as follows:

```
git clone https://github.com/canonical/falco-operators.git
```

Make sure to install [`uv`](https://docs.astral.sh/uv/). For example, you can install `uv` on Ubuntu using:

```bash
sudo snap install astral-uv --classic
```

For other systems, follow the [`uv` installation guide](https://docs.astral.sh/uv/getting-started/installation/).

Then install `tox` with its extensions, and install a range of Python versions:

```bash
uv python install
uv tool install tox --with tox-uv
uv tool update-shell
```

To create a development environment, run the following code in the library directory (not the repository root directory):

```bash
uv sync --all-groups
source .venv/bin/activate
```

### Test

This project uses `tox` for managing test environments. There are some pre-configured environments
that can be used for linting and formatting code when you're preparing contributions to the library:

* ``tox``: Executes all of the basic checks and tests (``lint``, ``unit``, ``static``, and ``coverage-report``).
* ``tox -e fmt``: Runs formatting using ``ruff``.
* ``tox -e lint``: Runs a range of static code analysis to check the code.
* ``tox -e static``: Runs other checks such as ``bandit`` for security issues.
* ``tox -e unit``: Runs the unit tests.
* ``tox -e integration``: Runs the integration tests.
