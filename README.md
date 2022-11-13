# novelai-api
Python API for the NovelAI REST API

This module is intended to be used by developers as a helper for using NovelAI's REST API.

[TODO]: # (Add Quality Checking workflows and badges)

| Category         | Badges                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
|------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Pypi             | [![PyPI](https://img.shields.io/pypi/v/novelai-api)](https://pypi.org/project/novelai-api) [![PyPI - Python Version](https://img.shields.io/pypi/pyversions/novelai-api)](https://pypi.org/project/novelai-api) [![PyPI - License](https://img.shields.io/pypi/l/novelai-api)](https://pypi.org/project/novelai-api/) [![PyPI - Format](https://img.shields.io/pypi/format/novelai-api)](https://pypi.org/project/novelai-api/)                                                                                                                                                                                                                                                                                               |
| Quality checking | [![Python package](https://github.com/Aedial/novelai-api/actions/workflows/python-package.yml/badge.svg)](https://github.com/Aedial/novelai-api/actions/workflows/python-package.yml) [![Python package](https://github.com/Aedial/novelai-api/actions/workflows/codeql-analysis.yml/badge.svg)](https://github.com/Aedial/novelai-api/actions/workflows/codeql-analysis.yml) [![linting: pylint](https://img.shields.io/badge/linting-pylint-yellowgreen)](https://github.com/PyCQA/pylint) [![security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit) [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black) |
| Stats            | ![GitHub top language](https://img.shields.io/github/languages/top/Aedial/novelai-api) ![Libraries.io dependency status for GitHub repo](https://img.shields.io/librariesio/github/Aedial/novelai-api) ![GitHub repo size](https://img.shields.io/github/repo-size/Aedial/novelai-api) ![GitHub issues](https://img.shields.io/github/issues-raw/Aedial/novelai-api) ![GitHub pull requests](https://img.shields.io/github/issues-pr-raw/Aedial/novelai-api)                                                                                                                                                                                                                                                                  |
| Activity         | ![GitHub last commit](https://img.shields.io/github/last-commit/Aedial/novelai-api) ![GitHub commits since tagged version](https://img.shields.io/github/commits-since/Aedial/novelai-api/v0.10.1) ![GitHub commit activity](https://img.shields.io/github/commit-activity/m/Aedial/novelai-api) ![Maintenance](https://img.shields.io/maintenance/yes/2022)                                                                                                                                                                                                                                                                                                                                                                  |


### Prerequisites
Before anything, ensure that poetry is installed (pip install poetry), and that the virtual env is installed and up-to-date (poetry install).
For loging in, credentials are needed (NAI_USERNAME and NAI_PASSWORD). They should be passed via the environment variables.

### Examples
The examples are in the example folder. Each example is standalone and can be used as a test.
Examples should be ran with `poetry run python example/<name>.py`.

Some tests act as example. The full list is as follows :
- decryption and re-encryption: tests/test_decrypt_encrypt_integrity_check.py
- diverse generations: tests/test_generate.py
- parallel generations: tests/test_generate_parallel.py

### Usage
The source and all the required functions are located in the novelai-api folder.
The examples and tests showcase how this API should be used and can be regarded as the "right way" to use it. However, it doesn't mean one can't use the "low level" part, which is a thin implementation of the REST endpoints, while the "high level" part is an abstraction built on that low level.

### Contributing
You can contribute features and enhancements through PR. Any PR should pass the tests and the pre-commits before submission.

The tests' dependencies should have been installed via poetry (see Prerequisites)
The tests can be ran with `poetry run pytest -n auto --tb=short tests`. Note that running `npm install fflate` and having node.js installed is required for test_decrypt_encrypt_integrity_check.py to run properly

To install the pre-commit hook, run `poetry run pre-commit install`
To run the pre-commit hook locally run `poetry run pre-commit run --verbose --all-files`
