# Python Project Template

## Project Init

- [ ] Update the `python_project/` example directory to the new package name. Be sure to fix imports in `__init__.py` and `__main__.py`
- [ ] Create a virtualenv for the minimum supported Python version. `Python>=3.8` should be sufficient for most projects.
- [ ] Update the `write_to` entry in `pyproject.toml`
- [ ] Update the specified lines in the `Makefile`
- [ ] Update the specified lines in `setup.cfg`
- [ ] Update the package name in `tox.ini`

## Adding or updating dependencies

New dependencies should be added to the `install_requires` section of the `setup.cfg` file.

Then, the `make requirements` command will create or update the `requirements.txt` file.

Finally, run `make init-pip` to sync the requirements to the currently activated virtualenv.

To update existing dependencies, use the `pip-tools` utility:

`pip-compile --update --upgrade-package package`

NOTE: Constrain dependency versions in the `setup.cfg` file e.g. `requests>=3.0.0`.

Libraries should never have pinned versions in the `setup.py` file.

## New and Existing Projects

When cloning or revisiting a project after some time, the `make init` command will update dependencies and pre-commit hooks.

The `make init-pip` command should be called if the `requirements.txt` file has been updated.

The `make init-hooks` command should be run whenever the `.pre-commit-config.yml` file is updated.

This make target will install the pip requirements specified in the `requirements.txt` file, install the python package under development mode, and install `pre-commit` hooks.

----

# Project Name

Add a short description of your project here.

## Installation

Add any extra steps needed for installation here, including external dependencies.
