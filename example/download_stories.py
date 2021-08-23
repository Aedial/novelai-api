from novelai_api import NovelAI_API
from novelai_api.utils import get_encryption_key, decrypt_stories
from aiohttp import ClientSession

from logging import Logger
from os.path import join
from asyncio import run

filename = join("credentials", "creds_example.txt")
with open(filename) as f:
	username, password = f.read().split(',')

logger = Logger("NovelAI")

async def main():
	async with ClientSession() as session:
		api = NovelAI_API(session, logger = logger)

		login = await api.high_level.login(username, password)
		print(login)
		assert login

		stories = await api.high_level.download_stories()
		assert stories

		key = get_encryption_key(username, password)
		keystore = await api.high_level.get_keystore(key)
		print(keystore)
		assert keystore

		decrypt_stories(stories, keystore)
		print(stories)


run(main())