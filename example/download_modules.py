"""
{filename}
==============================================================================

Example of how to download and decrypt modules from the provided account
"""

import asyncio

from example.boilerplate import API, dumps
from novelai_api.utils import decrypt_user_data, encrypt_user_data


async def main():
    async with API() as api_handler:
        api = api_handler.api
        logger = api_handler.logger
        key = api_handler.encryption_key

        keystore = await api.high_level.get_keystore(key)
        logger.info(repr(keystore))

        modules = await api.high_level.download_user_modules()
        decrypt_user_data(modules, keystore)
        logger.info(dumps(modules))

        # if you want to upload the modules after modifying
        encrypt_user_data(modules, keystore)


if __name__ == "__main__":
    asyncio.run(main())
