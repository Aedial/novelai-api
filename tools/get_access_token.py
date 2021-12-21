from os.path import join
from random import choice
from asyncio import run
from aiohttp import ClientSession

from novelai_api import NovelAI_API

filename = join("credentials", "creds_example.txt")
with open(filename) as f:
	lines = [line.strip() for line in f.readlines()]
	creds = [line for line in lines if line != "" and line[0] != "#"]
	username, password = choice(creds).split(',')

async def main():
	async with ClientSession() as session:
		api = NovelAI_API(session)
		print(f"Access token: {await api.high_level.login(username, password)}")

run(main())