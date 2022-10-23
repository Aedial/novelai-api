from asyncio import run

from boilerplate import API
from novelai_api.utils import decrypt_user_data


async def main():
    async with API() as api_handler:
        api = api_handler.api
        logger = api_handler.logger
        key = api_handler.encryption_key

        keystore = await api.high_level.get_keystore(key)
        logger.info(keystore)

        stories = await api.high_level.download_user_stories()
        decrypt_user_data(stories, keystore)
        logger.info(stories)


run(main())
