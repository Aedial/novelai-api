### Requirements
Requires the "NAI_USERNAME" and "NAI_PASSWORD" values provided via environment variables.
They can be provided through a .env file at the root of the project.

The "NAI_PROXY" environment variable is also supported to inject a proxy address.

### Usage
If you have the novelai-api package installed via pip :
```
python example/<filename>
```

<br/>

If you don't have the novelai-api package installed, or you're actively developing on the project :
```
poetry run python example/<filename>
```
Remember to run `poetry install` before running the example, if not already done.
