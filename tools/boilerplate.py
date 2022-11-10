from logging import Logger, StreamHandler
from aiohttp import ClientSession

from sys import path
from os.path import join, abspath, dirname

path.insert(0, abspath(join(dirname(__file__), '..')))
from novelai_api import NovelAIAPI
from novelai_api.utils import get_encryption_key

from typing import Optional


class API:
    _username: str
    _password: str
    _session: ClientSession

    logger: Logger
    api: Optional[NovelAIAPI]
    access_token: Optional[str]

    def __init__(self):
        from os import environ as env

        if "NAI_USERNAME" not in env or "NAI_PASSWORD" not in env:
            raise RuntimeError("Please ensure that NAI_USERNAME and NAI_PASSWORD are set in your environment")

        self._username = env["NAI_USERNAME"]
        self._password = env["NAI_PASSWORD"]

        self.logger = Logger("NovelAI")
        self.logger.addHandler(StreamHandler())

        self.api = NovelAIAPI(logger = self.logger)
        self.access_token = None

    @property
    def encryption_key(self):
        return get_encryption_key(self._username, self._password)

    async def __aenter__(self):
        self._session = ClientSession()
        await self._session.__aenter__()

        self.api.attach_session(self._session)
        self.access_token = await self.api.high_level.login(self._username, self._password)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._session.__aexit__(exc_type, exc_val, exc_tb)
