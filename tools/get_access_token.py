from os import environ as env
from os.path import join
from random import choice
from asyncio import run
from aiohttp import ClientSession

from novelai_api import NovelAI_API

if "NAI_USERNAME" not in env or "NAI_PASSWORD" not in env:
    exit("Please set the environment variables NAI_USERNAME and NAI_PASSWORD to your NAI username and password")

username = env["NAI_USERNAME"]
password = env["NAI_PASSWORD"]

async def main():
	async with ClientSession() as session:
		api = NovelAI_API(session)
		print(f"Access token: {await api.high_level.login(username, password)}")

run(main())