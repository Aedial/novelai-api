# novelai-api
Python API for the NovelAI REST API

This module is intended to be used by developers as a helper for using NovelAI's REST API.

[TODO]: # (Add Quality Checking workflows and badges)

| Category         | Badges                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
|------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Pypi             | [![PyPI](https://img.shields.io/pypi/v/novelai-api)](https://pypi.org/project/novelai-api) [![PyPI - Python Version](https://img.shields.io/pypi/pyversions/novelai-api)](https://pypi.org/project/novelai-api) [![PyPI - License](https://img.shields.io/pypi/l/novelai-api)](https://pypi.org/project/novelai-api/) [![PyPI - Format](https://img.shields.io/pypi/format/novelai-api)](https://pypi.org/project/novelai-api/)                                                                                                                                                                                                                                                                                               |
| Quality checking | [![Python package](https://github.com/Aedial/novelai-api/actions/workflows/python-package.yml/badge.svg)](https://github.com/Aedial/novelai-api/actions/workflows/python-package.yml) [![Python package](https://github.com/Aedial/novelai-api/actions/workflows/codeql-analysis.yml/badge.svg)](https://github.com/Aedial/novelai-api/actions/workflows/codeql-analysis.yml) [![linting: pylint](https://img.shields.io/badge/linting-pylint-yellowgreen)](https://github.com/PyCQA/pylint) [![security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit) [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black) |
| Stats            | [![GitHub top language](https://img.shields.io/github/languages/top/Aedial/novelai-api)](https://github.com/Aedial/novelai-api/search?l=python) ![Libraries.io dependency status for GitHub repo](https://img.shields.io/librariesio/github/Aedial/novelai-api) ![GitHub repo size](https://img.shields.io/github/repo-size/Aedial/novelai-api) ![GitHub issues](https://img.shields.io/github/issues-raw/Aedial/novelai-api) ![GitHub pull requests](https://img.shields.io/github/issues-pr-raw/Aedial/novelai-api)                                                                                                                                                                                                         |
| Activity         | ![GitHub last commit](https://img.shields.io/github/last-commit/Aedial/novelai-api) ![GitHub commits since tagged version](https://img.shields.io/github/commits-since/Aedial/novelai-api/v0.12.0) ![GitHub commit activity](https://img.shields.io/github/commit-activity/m/Aedial/novelai-api)                                                                                                                                                                                                                                                                                                                                                                                                                              |


# Usage
Download via [pip](https://pypi.org/project/novelai-api):
```
pip install novelai-api
```

A full list of examples is available in the [example](example) directory

The API works through the NovelAIAPI object.
It is split in 2 groups: NovelAIAPI.low_level and NovelAIAPI.high_level

## low_level
The low level interface is a strict implementation of the official API (<https://api.novelai.net/docs>).
It only checks for input types via assert, and output schema if NovelAIAPI.low_level.is_schema_validation_enabled is True

## high_level
The high level interface builds on the low level one for easier handling of complex settings.
It handles many tasks from the frontend


# Development
All relevant objects are in the [novelai_api](novelai_api) directory. The [nox](https://pypi.org/project/nox/) package is required (`pip install nox`).

## Contributing
You can contribute features and enhancements through PR. Any PR should pass the tests and the pre-commits before submission.
The pre-commit hook can be installed via
```
nox -s pre-commit
```

## Testing against the API
[API](tests/api)

## Testing against the mocked API
| :warning: WIP, does not work yet :warning: |
|--------------------------------------------|

[Mock](tests/mock)

## Docs
To build the docs, run
```
nox -s build-docs
```
The docs will be locally viewable at docs/build/html/index.html
