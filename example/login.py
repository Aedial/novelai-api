from sys import version_info, path
from os.path import join, abspath, dirname
path.insert(0, abspath(join(dirname(__file__), '..')))

from novelai_api import NovelAI_API
from aiohttp import ClientSession

from logging import Logger
from asyncio import run

filename = join("credentials", "creds_example.txt")
with open(filename) as f:
	username, password = f.read().split(',')

logger = Logger("NovelAI")

async def main():
	async with ClientSession() as session:
		api = NovelAI_API(session, logger = logger)
		print(await api.high_level.login(username, password))

run(main())