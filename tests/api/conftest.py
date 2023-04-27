import asyncio

import pytest


# cannot put in boilerplate because pytest is a mess
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()
