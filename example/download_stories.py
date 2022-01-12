from sys import path
from os import environ as env
from os.path import join, abspath, dirname

path.insert(0, abspath(join(dirname(__file__), '..')))

from novelai_api import NovelAI_API
from novelai_api.utils import get_encryption_key, decrypt_user_data
from aiohttp import ClientSession

from logging import Logger, StreamHandler
from asyncio import run

if "NAI_USERNAME" not in env or "NAI_PASSWORD" not in env:
    raise RuntimeError("Please ensure that NAI_USERNAME and NAI_PASSWORD are set in your environment")

username = env["NAI_USERNAME"]
password = env["NAI_PASSWORD"]

logger = Logger("NovelAI")
logger.addHandler(StreamHandler())

async def main():
    async with ClientSession() as session:
        api = NovelAI_API(session, logger = logger)

        login = await api.high_level.login(username, password)
        logger.info(login)

        key = get_encryption_key(username, password)
        keystore = await api.high_level.get_keystore(key)
        logger.info(keystore)

        stories = await api.high_level.download_user_stories()
        decrypt_user_data(stories, keystore)
        logger.info(stories)


run(main())