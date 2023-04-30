import asyncio
import functools
import json
from logging import Logger, StreamHandler
from os import environ as env
from typing import Any, Awaitable, Callable, NoReturn, Optional

import pytest
from aiohttp import ClientConnectionError, ClientPayloadError, ClientSession

from novelai_api import NovelAIAPI, NovelAIError
from novelai_api.utils import get_encryption_key


class API:
    _username: str
    _password: str
    _session: ClientSession
    _sync: bool

    logger: Logger
    api: NovelAIAPI

    def __init__(self, sync: bool = False):
        if "NAI_USERNAME" not in env or "NAI_PASSWORD" not in env:
            raise RuntimeError("Please ensure that NAI_USERNAME and NAI_PASSWORD are set in your environment")

        self._username = env["NAI_USERNAME"]
        self._password = env["NAI_PASSWORD"]
        self._sync = sync

        self.logger = Logger("NovelAI")
        self.logger.addHandler(StreamHandler())

        proxy = env["NAI_PROXY"] if "NAI_PROXY" in env else None

        self.api = NovelAIAPI(logger=self.logger)
        self.api.proxy = proxy

    @property
    def encryption_key(self):
        return get_encryption_key(self._username, self._password)

    def __enter__(self) -> NoReturn:
        raise TypeError("Use async with instead")

    async def __aenter__(self):
        if not self._sync:
            self._session = ClientSession()
            await self._session.__aenter__()
            self.api.attach_session(self._session)

        await self.api.high_level.login(self._username, self._password)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if not self._sync:
            await self._session.__aexit__(exc_type, exc_val, exc_tb)


def error_handler(func_ext: Optional[Callable[[Any, Any], Awaitable[Any]]] = None, *, attempts: int = 5, wait: int = 5):
    """
    Decorator to add error handling to the decorated function
    The function must accept an API object as first arguments

    :param func_ext: Substitute for func if the decorator is run without argument. Do not provide it directly
    :param attempts: Number of attempts to do before raising the error
    :param wait: Time (in seconds) to wait after each call
    """

    def decorator(func: Callable[[Any, Any], Awaitable[Any]]):
        @functools.wraps(func)
        async def wrap(*args, **kwargs):
            err: Exception = RuntimeError("Error placeholder. Shouldn't happen")
            for _ in range(attempts):
                try:
                    res = await func(*args, **kwargs)
                    await asyncio.sleep(wait)

                    return res
                except (ClientConnectionError, asyncio.TimeoutError, ClientPayloadError) as e:
                    err = e
                    retry = True

                except NovelAIError as e:
                    err = e
                    retry = any(
                        [
                            e.status == 502,  # Bad Gateway
                            e.status == 520,  # Cloudflare Unknown Error
                            e.status == 524,  # Cloudflare Gateway Error
                        ]
                    )

                if not retry:
                    break

                # 10s wait between each retry
                await asyncio.sleep(10)

                # no internet: ping every 5 mins until connection is re-established
                async with ClientSession() as session:
                    while True:
                        try:
                            rsp = await session.get("https://www.google.com", timeout=5 * 60)
                            rsp.raise_for_status()

                            break
                        except ClientConnectionError:
                            await asyncio.sleep(5 * 60)
                        except asyncio.TimeoutError:
                            pass

            raise err

        return wrap

    # allow to run the function without argument
    if func_ext is None:
        return decorator

    return decorator(func_ext)


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


@pytest.fixture(scope="session")
async def api_handle():
    """
    API handle for an Async Test. Use it as a pytest fixture
    """

    async with API() as api:
        yield api


@pytest.fixture(scope="session")
async def api_handle_sync():
    """
    API handle for a Sync Test. Use it as a pytest fixture
    """

    async with API(sync=True) as api:
        yield api
