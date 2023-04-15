from asyncio import run

from boilerplate import API, dumps

from novelai_api.utils import compress_user_data, decompress_user_data


async def main():
    async with API() as api_handler:
        api = api_handler.api
        logger = api_handler.logger

        shelves = await api.high_level.download_user_shelves()
        decompress_user_data(shelves)
        logger.info(dumps(shelves))

        # if you want to upload the shelves after modifying
        compress_user_data(shelves)


run(main())
