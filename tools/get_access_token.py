from asyncio import run

from boilerplate import API


async def main():
    async with API() as api_handler:
        print(f"Access token: {api_handler.access_token}")


run(main())
