from sys import path
from os import environ as env
from os.path import join, abspath, dirname

from argparse import ArgumentParser

path.insert(0, abspath(join(dirname(__file__), '..')))

from novelai_api import NovelAI_API
from novelai_api.utils import get_encryption_key, decrypt_user_data, assign_content_to_story
from aiohttp import ClientSession

from logging import Logger, StreamHandler
from asyncio import run
from json import dumps

if "NAI_USERNAME" not in env or "NAI_PASSWORD" not in env:
    raise RuntimeError("Please ensure that NAI_USERNAME and NAI_PASSWORD are set in your environment")

username = env["NAI_USERNAME"]
password = env["NAI_PASSWORD"]

logger = Logger("NovelAI")
logger.addHandler(StreamHandler())

async def main():
    parser = ArgumentParser()
    parser.add_argument("directory", nargs = "?", default = ".", help = "Directory to dump the stories to")

    args = parser.parse_args()

    async with ClientSession() as session:
        api = NovelAI_API(session, logger = logger)

        login = await api.high_level.login(username, password)

        key = get_encryption_key(username, password)
        keystore = await api.high_level.get_keystore(key)

        stories = await api.high_level.download_user_stories()
        decrypt_user_data(stories, keystore)

        story_contents = await api.high_level.download_user_story_contents()
        decrypt_user_data(story_contents, keystore)

        assign_content_to_story(stories, story_contents)

        for i, story in enumerate(stories):
            if story.get("decrypted") and "content" in story:
                name = story["data"]["title"]
                path = join(args.directory, f"{i}-{name}.scenario")

                # shouldn't been shared
                for e in (story, story["content"]):
                    del e["nonce"]
                    del e["decrypted"]
                    del e["compressed"]

                content = {"storyContainerVersion": 1}
                content["metadata"] = story["data"]
                content["content"] = story["content"]["data"]

                # remove useless keys
                del content["metadata"]["remoteStoryId"]
                if "remoteId" in content["metadata"]:
                    del content["metadata"]["remoteId"]

                with open(path, "w") as f:
                    f.write(dumps(content, ensure_ascii = False, indent = 2))

run(main())