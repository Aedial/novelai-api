from os.path import join
from random import choice

from novelai_api.utils import get_access_key

filename = join("credentials", "creds_example.txt")
with open(filename) as f:
	lines = [line.strip() for line in f.readlines()]
	creds = [line for line in lines if line != "" and line[0] != "#"]
	username, password = choice(creds).split(',')

print(get_access_key(username, password))