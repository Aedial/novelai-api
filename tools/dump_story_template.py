from asyncio import run
from json import dumps

from boilerplate import API

from novelai_api.utils import decrypt_user_data

# step 1: make a new, empty story on NAI
# step 2: switch on/off remote storage to upload it


# step 3: launch the code
async def main():
    async with API() as api_handler:
        api = api_handler.api
        encryption_key = api_handler.encryption_key

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

        with open("template_story.txt", "w", encoding="utf-8") as f:
            print(dumps(empty_story), file=f)

        with open("template_storycontent.txt", "w", encoding="utf-8") as f:
            print(dumps(empty_storycontent), file=f)


run(main())

# step 4: delete the (new) empty story
