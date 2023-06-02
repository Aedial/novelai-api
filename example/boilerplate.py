import json
from logging import Logger, StreamHandler
from os import environ as env
from typing import Any, Optional

import dotenv
from aiohttp import ClientSession

from novelai_api import NovelAIAPI
from novelai_api.utils import get_encryption_key


class API:
    """
    Boilerplate for the redundant parts.
    Using the object as a context manager will automatically login using the environment variables
    ``NAI_USERNAME`` and ``NAI_PASSWORD``.

    Usage:

    .. code-block:: python

        async with API() as api:
            api = api.api
            encryption_key = api.encryption_key
            logger = api.logger
            ...  # Do stuff


    A custom base address can be passed to the constructor to replace the default
    (:attr:`BASE_ADDRESS <novelai_api.NovelAI_API.NovelAIAPI.BASE_ADDRESS>`)
    """

    _username: str
    _password: str
    _session: ClientSession

    logger: Logger
    api: Optional[NovelAIAPI]

    def __init__(self, base_address: Optional[str] = None):
        dotenv.load_dotenv()

        if "NAI_USERNAME" not in env or "NAI_PASSWORD" not in env:
            raise RuntimeError("Please ensure that NAI_USERNAME and NAI_PASSWORD are set in your environment")

        self._username = env["NAI_USERNAME"]
        self._password = env["NAI_PASSWORD"]

        self.logger = Logger("NovelAI")
        self.logger.addHandler(StreamHandler())

        self.api = NovelAIAPI(logger=self.logger)
        if base_address is not None:
            self.api.BASE_ADDRESS = base_address

    @property
    def encryption_key(self):
        return get_encryption_key(self._username, self._password)

    async def __aenter__(self):
        self._session = ClientSession()
        await self._session.__aenter__()

        self.api.attach_session(self._session)
        await self.api.high_level.login(self._username, self._password)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._session.__aexit__(exc_type, exc_val, exc_tb)


class JSONEncoder(json.JSONEncoder):
    """
    Extended JSON encoder to support bytes
    """

    def default(self, o: Any) -> Any:
        if isinstance(o, bytes):
            return o.hex()

        return super().default(o)


def dumps(e: Any) -> str:
    """
    Shortcut to a configuration of json.dumps for consistency
    """

    return json.dumps(e, indent=4, ensure_ascii=False, cls=JSONEncoder)
