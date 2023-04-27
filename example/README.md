### Requirements
Requires the "NAI_USERNAME" and "NAI_PASSWORD" values provided via environment variables.

The "NAI_PROXY" environment variable is also supported to inject a proxy address.

### Usage
If you have the novelai-api package installed via pip :
```
python example/<filename>
```

<br/>

If you don't have the novelai-api package installed, or you're actively developing on the project :
```
nox -s run -- example/<filename>
```
This option supports providing environment variables through a .env file
