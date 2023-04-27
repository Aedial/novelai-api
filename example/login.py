"""
{filename}
==============================================================================

Example of how to login on the provided account
"""

import asyncio

from example.boilerplate import API


async def main():
    async with API() as api_handler:  # noqa: F841  # pylint: disable=W0612
        print(api_handler.api.headers)


if __name__ == "__main__":
    asyncio.run(main())
