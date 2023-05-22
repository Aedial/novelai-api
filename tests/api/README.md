### Requirements
Requires the "NAI_USERNAME" and "NAI_PASSWORD" values provided via environment variables.
They can be provided through a .env file at the root of the project.

The "NAI_PROXY" environment variable is also supported to inject a proxy address.

### Usage
For running all the tests under the tests/api folder :
```
poetry run nai-test-api
```

For running a specific test files (using the [pytest name scheme](https://docs.pytest.org/en/7.3.x/how-to/usage.html#nodeids)) :
```
poetry run nai-test-api <filename 1> ... <filename n>
```

Remember to run `poetry install` before running the test, if not already done.
