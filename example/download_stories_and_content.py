"""
{filename}
==============================================================================

Example of how to download and decrypt stories from the provided account
"""

import asyncio

from example.boilerplate import API, dumps
from novelai_api.utils import decrypt_user_data, encrypt_user_data, link_content_to_story, unlink_content_from_story


async def main():
    async with API() as api_handler:
        api = api_handler.api
        logger = api_handler.logger
        key = api_handler.encryption_key

        keystore = await api.high_level.get_keystore(key)
        logger.info(repr(keystore))

        stories = await api.high_level.download_user_stories()
        decrypt_user_data(stories, keystore)

        story_contents = await api.high_level.download_user_story_contents()
        decrypt_user_data(story_contents, keystore)

        # match stories and story contents
        link_content_to_story(stories, story_contents)
        logger.info(dumps(stories))
        # remove the story_contents from stories
        unlink_content_from_story(stories)

        # if you want to upload the stories after modifying
        encrypt_user_data(stories, keystore)

        # if you want to upload the story_contents after modifying
        encrypt_user_data(story_contents, keystore)


if __name__ == "__main__":
    asyncio.run(main())
