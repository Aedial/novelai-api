from sys import path
from os import environ as env
from os.path import join, abspath, dirname

path.insert(0, abspath(join(dirname(__file__), '..')))

from novelai_api import NovelAI_API
from novelai_api.utils import get_encryption_key, decrypt_user_data, encrypt_user_data, decompress_user_data, compress_user_data
from aiohttp import ClientSession

from asyncio import run

#from js2py import require

from typing import List, Dict, Any

def compare_in_out(type_name: str, items_in: List[Dict[str, Any]], items_out: List[Dict[str, Any]]) -> bool:
    fail_flags = ''.join(('O' if item_in == item_out else 'X') for item_in, item_out in zip(items_in, items_out))
    if 'X' in fail_flags:
        print(f"{fail_flags.count('X')}/{len(fail_flags)} integrity checks failed for {type_name}")
        print(fail_flags)
        print("")

        return False
    else:
        print(f"All {len(fail_flags)} integrity checks succeeded for {type_name}\n")
        return True

"""
fflate = require("fflate")

def inflate_js(data: bytes, wbits: int) -> bytes:
    b64_arr = b64encode(data).decode()
    print(b64_arr)
    arr = fflate.strToU8(b64_arr, "base64")
    print(type(arr))
    res = fflate.inflateSync(arr)
    print(res)

    return res
"""

if "NAI_USERNAME" not in env or "NAI_PASSWORD" not in env:
    raise RuntimeError("Please ensure that NAI_USERNAME and NAI_PASSWORD are set in your environment")

username = env["NAI_USERNAME"]
password = env["NAI_PASSWORD"]

async def run_with_api(api: NovelAI_API):
    await api.high_level.login(username, password)

    success = True

    key = get_encryption_key(username, password)
    keystore = await api.high_level.get_keystore(key)

    encrypted_keystore_in = [str(keystore.data)]
    keystore.encrypt(key)
    encrypted_keystore_out = [str(keystore.data)]
    success = compare_in_out("keystore", encrypted_keystore_in, encrypted_keystore_out) and success

    stories = await api.high_level.download_user_stories()
    encrypted_stories_in = [str(story) for story in stories]
    decrypt_user_data(stories, keystore)
    encrypt_user_data(stories, keystore)
    encrypted_stories_out = [str(story) for story in stories]
    success = compare_in_out("stories", encrypted_stories_in, encrypted_stories_out) and success

    story_contents = await api.high_level.download_user_story_contents()
    decrypt_user_data(story_contents, keystore)
    decrypted_storycontent_in = [str(story_content) for story_content in story_contents]
    encrypt_user_data(story_contents, keystore)

    # FIXME: make js2py work with fflate. Atm, it just fails saying the data is corrupted
    # different logic, as zlib yields different (but fully compatible) results as fflate
    # so, we inject the js decompression directly, to test
#    inflate_backup = utils.inflate
#    utils.inflate = inflate_js
    decrypt_user_data(story_contents, keystore)
#    utils.inflate = inflate_backup

    decrypted_storycontent_out = [str(story_content) for story_content in story_contents]
    success = compare_in_out("storycontent", decrypted_storycontent_in, decrypted_storycontent_out) and success

    presets = await api.high_level.download_user_presets()
    encrypted_presets_in = [str(preset) for preset in presets]
    decompress_user_data(presets)
    compress_user_data(presets)
    encrypted_presets_out = [str(preset) for preset in presets]
    success = compare_in_out("presets", encrypted_presets_in, encrypted_presets_out) and success

    modules = await api.high_level.download_user_modules()
    encrypted_modules_in = [str(module) for module in modules]
    decrypt_user_data(modules, keystore)
    encrypt_user_data(modules, keystore)
    encrypted_modules_out = [str(module) for module in modules]
    success = compare_in_out("aimodules", encrypted_modules_in, encrypted_modules_out) and success

    # TODO: add shelves

    if not success:
        raise RuntimeError("Some encryption/decryption integrity checks failed")

async def main():
    # async handler
    async with ClientSession() as session:
        api = NovelAI_API(session)
        await run_with_api(api)

    # sync handler
    api = NovelAI_API()
    await run_with_api(api)

run(main())