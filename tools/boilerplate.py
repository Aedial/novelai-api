from logging import Logger, StreamHandler
from os.path import abspath, dirname, join
from sys import path
from typing import Optional

from aiohttp import ClientSession

# pylint: disable=C0413,C0415
path.insert(0, abspath(join(dirname(__file__), "..")))
from novelai_api import NovelAIAPI
from novelai_api.utils import get_encryption_key


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

        self.api = NovelAIAPI(logger=self.logger)
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
