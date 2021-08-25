# novelai-api
Python API for the NovelAI REST API

The module is intended to be used by developers as a help for using NovelAI's REST API.


## Prerequisites:
For loging in, credentials are needed. They should be placed into /credentials/<filename>.txt with <filename> depending on the script to execute.


### Examples:
The examples are in the example folder. Each example is working and can be used as a test.
Each example can be called with `python <name>.py`.


### Tests:
The test suite is WIP and can be called with `python tests/test.py [-n <number of iterations>] [--no-login] [--side-effect]`.
A login will be require unless --no-login is passed
--side-effect will allow the class to modify things on the logged account, and can have undesired effects (so use it with caution !).


### Module:
The actual module is in the novelai-api folder. Valid imports are : `novelai_api.NovelAI_API`, `novelai_api.NovelAIError`, and everything under the `novelai_api.utils` namespace.
This module is asynchronous, and, as such, must be run with asyncio. An example can be found in any file of the example directory.
The module is registered as package under [Pypi](https://pypi.org/project/novelai-api/).