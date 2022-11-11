from sys import path
from os.path import join, abspath, dirname
from os import environ as env

path.insert(0, abspath(join(dirname(__file__), "..")))

from novelai_api.utils import get_access_key

if "NAI_USERNAME" not in env or "NAI_PASSWORD" not in env:
    exit("Please set the environment variables NAI_USERNAME and NAI_PASSWORD to your NAI username and password")

username = env["NAI_USERNAME"]
password = env["NAI_PASSWORD"]

print(get_access_key(username, password))
