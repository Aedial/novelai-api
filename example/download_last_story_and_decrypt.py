import asyncio
from pathlib import Path

from example.boilerplate import API, dumps
from novelai_api.utils import decrypt_user_data

dump_file = Path(__file__).parent.parent / "results" / "story.json"


async def main():
    async with API() as api_handler:
        api = api_handler.api
        key = api_handler.encryption_key

        keystore = await api.high_level.get_keystore(key)

        story = (await api.high_level.download_user_stories())[0]
        decrypt_user_data(story, keystore)

        storycontent_id = story["data"]["remoteStoryId"]

        story_contents = await api.low_level.download_object("storycontent", storycontent_id)
        decrypt_user_data(story_contents, keystore, True)

        dump_file.parent.mkdir(exist_ok=True)
        dump_file.write_text(dumps(story_contents), "utf-8")


if __name__ == "__main__":
    asyncio.run(main())
