from argparse import ArgumentParser
from asyncio import run
from json import dumps
from pathlib import Path

from boilerplate import API

from novelai_api.utils import decrypt_user_data, link_content_to_story


async def main():
    parser = ArgumentParser()
    parser.add_argument("directory", nargs="?", default=".", help="Directory to dump the stories to")

    args = parser.parse_args()

    async with API() as api_handler:
        api = api_handler.api
        key = api_handler.encryption_key

        keystore = await api.high_level.get_keystore(key)

        stories = await api.high_level.download_user_stories()
        decrypt_user_data(stories, keystore)

        story_contents = await api.high_level.download_user_story_contents()
        decrypt_user_data(story_contents, keystore)

        link_content_to_story(stories, story_contents)

        for i, story in enumerate(stories):
            if story.get("decrypted") and "content" in story:
                name = story["data"]["title"]
                path = Path(args.directory) / f"{i}-{name}.scenario"

                # shouldn't be shared
                for e in (story, story["content"]):
                    del e["nonce"]
                    del e["decrypted"]
                    del e["compressed"]

                content = {
                    "storyContainerVersion": 1,
                    "metadata": story["data"],
                    "content": story["content"]["data"],
                }

                # remove useless keys
                del content["metadata"]["remoteStoryId"]
                if "remoteId" in content["metadata"]:
                    del content["metadata"]["remoteId"]

                with open(path, "w", encoding="utf-8") as f:
                    f.write(dumps(content, ensure_ascii=False, indent=2))


run(main())
