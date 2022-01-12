from sys import path
from os import environ as env
from os.path import join, abspath, dirname

path.insert(0, abspath(join(dirname(__file__), '..')))

from novelai_api import NovelAI_API
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
        logger.info(await api.high_level.login(username, password))

run(main())