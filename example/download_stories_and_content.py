import json
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

        # delete the nonce as it is not dump'able
        for story in stories:
            if "nonce" in story:
                del story["nonce"]

        logger.info(json.dumps(stories, indent=4, ensure_ascii=False))

        story_contents = await api.high_level.download_user_story_contents()
        decrypt_user_data(story_contents, keystore)

        logger.info("\n\n\n")

        # delete the nonce as it is not dump'able
        for story_content in story_contents:
            if "nonce" in story_content:
                del story_content["nonce"]

        logger.info(json.dumps(story_contents, indent=4, ensure_ascii=False))


run(main())
