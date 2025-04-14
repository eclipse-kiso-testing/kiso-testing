[![License](https://img.shields.io/badge/Licence-Eclipse%20Public%20License%202.0-lightgrey)](https://opensource.org/licenses/EPL-2.0)
[![Platforms](https://img.shields.io/badge/Platforms-win64%20linux64%20osx64-lightgrey)]()
[![Supported python version](https://img.shields.io/pypi/pyversions/pykiso)]()
![Build status](https://img.shields.io/github/actions/workflow/status/eclipse-kiso-testing/kiso-testing/verification_validation.yml)
[![Documentation Status](https://readthedocs.org/projects/kiso-testing/badge/?version=latest)](https://kiso-testing.readthedocs.io/en/latest/?badge=latest)
[![codecov](https://codecov.io/gh/eclipse-kiso-testing/kiso-testing/graph/badge.svg?token=IBKQ700ABS)](https://codecov.io/gh/eclipse-kiso-testing/kiso-testing)
[![CodeFactor](https://www.codefactor.io/repository/github/eclipse/kiso-testing/badge)](https://www.codefactor.io/repository/github/eclipse/kiso-testing)
[![Last commit](https://img.shields.io/github/last-commit/eclipse/kiso-testing)]()
[![Commits since latest version](https://img.shields.io/github/commits-since/eclipse/kiso-testing/latest/master)]()

# PyKiso

![Optional Text](./docs/images/pykiso_logo.png)

## Introduction ##

**pykiso** is an integration test framework. With it, it is possible to write
* Whitebox integration tests directly on my target device
* Graybox integration tests to make sure the communication-link with my target device is working as expected
* Blackbox integration tests to make sure my external device interfaces are working as expected

The project will contain:
* The core python framework (this repository)
* Framework plugins that are generic enough to be integrated as "native" (this repository)
* Additional "testApps" for different targets platforms (e.g. stm32, ...) or languages (C, C++, ...) . It could be pure SW or also HW (other repositories)

## Link to Eclipse Project
https://projects.eclipse.org/projects/iot.kiso-testing

## Requirements ##

* Python 3.10+
* pip/poetry (used to get the rest of the requirements)

## Install ##

```bash
pip install pykiso # Core framework
pip install pykiso[plugins] # For installing all plugins
pip install pykiso[all] # For installing all what we have to offer
```

[Poetry](https://python-poetry.org/) is more appropriate for developers as it automatically creates virtual environments.

```bash
cd kiso-testing
poetry install --all-extras
poetry shell
```

### Pre-Commit

To improve code-quality, a configuration of [pre-commit](https://pre-commit.com/) hooks are available.
The following pre-commit hooks are used:

- ruff-format
- flake8
- isort
- trailing-whitespace
- end-of-file-fixer
- check-docstring-first
- check-json
- check-added-large-files
- check-yaml
- debug-statements

If you don't have pre-commit installed, you can get it using pip:

```bash
pip install pre-commit
```

Start using the hooks with

```bash
pre-commit install
```

## Commit message convention

Commits are sorted into multiple categories based on keywords that can occur at any position as part of the commit message.
[Category] Keywords
* [BREAKING CHANGES] BREAKING CHANGE
* [Features] feat:
* [Fixes] fix:
* [Docs] docs:
* [Styles] style:
* [Refactors] refactor!:
* [Performances] perf:
* [Tests] test:
* [Build] build:
* [Ci] ci:
Each commit is considered only once according to the order of the categories listed above. Merge commits are ignored.

The tool commitizen can help you to create commits which follows these standards.
```bash
# if not yet installed:
pip install -U commitizen==2.20.4
# helps you to create a commit:
cz commit
# or use equivalent short variant:
cz c
```

## Generate Changelog

After you installed the dev dependencies from the pipfile you are able to
autogenerate the Changelog.

```bash
invoke changelog
```

## Usage ##

Once installed the application is bound to `pykiso`, it can be called with the following arguments:

```bash
Usage: pykiso [OPTIONS]

  Embedded Integration Test Framework - CLI Entry Point.

  TAG Filters: any additional option to be passed to the test as tag through
  the pykiso call. Multiple values must be separated with a comma.

  For example: pykiso -c your_config.yaml --branch-level dev,master --variant
  delta

Options:
  -c, --test-configuration-file FILE
                                  path to the test configuration file (in YAML
                                  format)  [required]
  -l, --log-path PATH             path to log-file or folder. If not set will
                                  log to STDOUT
  --log-level [DEBUG|INFO|WARNING|ERROR]
                                  set the verbosity of the logging
  --junit                         enables the generation of a junit report
  --text                          default, test results are only displayed in
                                  the console
  --step-report PATH              generate the step report at the specified
                                  path
  --failfast                      stop the test run on the first error or
                                  failure
  -v, --verbose                   activate the internal framework logs
  -p, --pattern TEXT              test filter pattern, e.g. 'test_suite_1.py'
                                  or 'test_*.py'. Or even more granularly
                                  'test_suite_1.py::test_class::test_name'
  --version                       Show the version and exit.
  -h, --help                      Show this message and exit.
  --logger                        Change the logger class used in pykiso, value
                                  is the import path to the logger class, example
                                  'logging.Logger'
```

Suitable config files are available in the `examples` folder.

### Demo using example config ##

```bash
invoke run
```

### Running the Tests ##

```bash
invoke test
```

or

```bash
pytest
```
