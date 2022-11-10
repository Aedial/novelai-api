from boilerplate import API

from asyncio import run


async def main():
	async with API() as api_handler:
		print(f"Access token: {api_handler.access_token}")

run(main())
