from novelai_api import NovelAI_API
from novelai_api.utils import decrypt_user_data, get_encryption_key

from aiohttp import ClientSession
from asyncio import run
from json import dumps
from os import environ as env
from sys import exit

# step 1: make a new, empty story on NAI
# step 2: switch on/off remote storage to upload it

# step 3: launch the code
async def main():
    async with ClientSession() as session:
        api = NovelAI_API(session)

        if "NAI_USERNAME" not in env or "NAI_PASSWORD" not in env:
            exit("Please set the environment variables NAI_USERNAME and NAI_PASSWORD to your NAI username and password")

        username = env["NAI_USERNAME"]
        password = env["NAI_PASSWORD"]

        await api.high_level.login(username, password)

        encryption_key = get_encryption_key(username, password)
        keystore = await api.high_level.get_keystore(encryption_key)

        empty_story = (await api.high_level.download_user_stories())[-1]
        empty_storycontent = (await api.high_level.download_user_story_contents())[-1]

        decrypt_user_data(empty_story, keystore)
        decrypt_user_data(empty_storycontent, keystore)

        # remove injected data
        for e in (empty_story, empty_storycontent):
            del e["compressed"]
            del e["decrypted"]
            del e["nonce"]

        with open("template_story.txt", 'w') as f:
            print(dumps(empty_story, separators = (',', ':')), file = f)

        with open("template_storycontent.txt", 'w') as f:
            print(dumps(empty_storycontent, indent = 4), file = f)

run(main())

# step 4: delete the (new) empty story