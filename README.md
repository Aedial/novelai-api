[![Python package](https://github.com/arthus-leroy/novelai-api/actions/workflows/python-package.yml/badge.svg?branch=main)](https://github.com/arthus-leroy/novelai-api/actions/workflows/python-package.yml)

# novelai-api
Python API for the NovelAI REST API

The module is intended to be used by developers as a help for using NovelAI's REST API.


## Prerequisites:
For loging in, credentials are needed (NAI_USERNAME and NAI_PASSWORD). They should be passed from the environment variables.


### Examples:
The examples are in the example folder. Each example is working and can be used as a test.
Each example can be called with `python <name>.py`.


### Tests:
The tests can be called with `pytest -n auto --tb=short tests`. Note that running `npm install fflate` and having node.js installed is required for test_decrypt_encrypt_integrity_check to run properly


### Module:
The actual module is in the novelai-api folder.
This module is asynchronous, and, as such, must be run with asyncio. An example can be found in any file of the example directory.
The module is registered as package under [Pypi](https://pypi.org/project/novelai-api/).