from sys import path
from os import environ as env
from os.path import join, abspath, dirname

path.insert(0, abspath(join(dirname(__file__), '..')))

from novelai_api import NovelAI_API, utils
from novelai_api.utils import get_encryption_key, decrypt_user_data, encrypt_user_data, decompress_user_data, compress_user_data

from aiohttp import ClientSession
from base64 import b64encode
from subprocess import Popen, PIPE

from asyncio import run

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

fflate_path = join(dirname(abspath(__file__)), "fflate_inflate.js")

def inflate_js(data: bytes, wbits: int) -> bytes:
    p = Popen(["node", fflate_path, str(len(data))], stdin = PIPE, stdout = PIPE)
    out, _ = p.communicate(data)

    return out

if "NAI_USERNAME" not in env or "NAI_PASSWORD" not in env:
    raise RuntimeError("Please ensure that NAI_USERNAME and NAI_PASSWORD are set in your environment")

username = env["NAI_USERNAME"]
password = env["NAI_PASSWORD"]

async def keystore_integrity(api: NovelAI_API):
    api.timeout = 30

    await api.high_level.login(username, password)

    key = get_encryption_key(username, password)
    keystore = await api.high_level.get_keystore(key)

    encrypted_keystore_in = [str(keystore.data)]
    keystore.encrypt(key)
    encrypted_keystore_out = [str(keystore.data)]

    assert compare_in_out("keystore", encrypted_keystore_in, encrypted_keystore_out)

async def test_keystore_integrity_sync():
    # sync handler
    api = NovelAI_API()
    await keystore_integrity(api)

async def test_keystore_integrity_async():
    # async handler
    try:
        async with ClientSession() as session:
            api = NovelAI_API(session)
            await keystore_integrity(api)
    except Exception as e:
        await session.close()
        raise e


async def stories_integrity(api: NovelAI_API):
    api.timeout = 30

    await api.high_level.login(username, password)

    key = get_encryption_key(username, password)
    keystore = await api.high_level.get_keystore(key)

    stories = await api.high_level.download_user_stories()
    encrypted_stories_in = [str(story) for story in stories]
    decrypt_user_data(stories, keystore)
    encrypt_user_data(stories, keystore)
    encrypted_stories_out = [str(story) for story in stories]

    assert compare_in_out("stories", encrypted_stories_in, encrypted_stories_out)

async def test_stories_integrity_sync():
    # sync handler
    api = NovelAI_API()
    await stories_integrity(api)

async def test_stories_integrity_async():
    # async handler
    try:
        async with ClientSession() as session:
            api = NovelAI_API(session)
            await stories_integrity(api)
    except Exception as e:
        await session.close()
        raise e


async def storycontent_integrity(api: NovelAI_API):
    api.timeout = 30

    await api.high_level.login(username, password)

    key = get_encryption_key(username, password)
    keystore = await api.high_level.get_keystore(key)

    story_contents = await api.high_level.download_user_story_contents()
    decrypt_user_data(story_contents, keystore)
    decrypted_storycontent_in = [str(story_content) for story_content in story_contents]
    encrypt_user_data(story_contents, keystore)

    inflate_backup = utils.inflate
    utils.inflate = inflate_js
    decrypt_user_data(story_contents, keystore)
    utils.inflate = inflate_backup

    decrypted_storycontent_out = [str(story_content) for story_content in story_contents]

    assert compare_in_out("storycontent", decrypted_storycontent_in, decrypted_storycontent_out)

async def test_storycontent_integrity_sync():
    # sync handler
    api = NovelAI_API()
    await storycontent_integrity(api)

async def test_storycontent_integrity_async():
    # async handler
    try:
        async with ClientSession() as session:
            api = NovelAI_API(session)
            await storycontent_integrity(api)
    except Exception as e:
        await session.close()
        raise e


async def presets_integrity(api: NovelAI_API):
    api.timeout = 30

    await api.high_level.login(username, password)

    key = get_encryption_key(username, password)

    presets = await api.high_level.download_user_presets()
    encrypted_presets_in = [str(preset) for preset in presets]
    decompress_user_data(presets)
    compress_user_data(presets)
    encrypted_presets_out = [str(preset) for preset in presets]

    assert compare_in_out("presets", encrypted_presets_in, encrypted_presets_out)

async def test_presets_integrity_sync():
    # sync handler
    api = NovelAI_API()
    await presets_integrity(api)

async def test_presets_integrity_async():
    # async handler
    try:
        async with ClientSession() as session:
            api = NovelAI_API(session)
            await presets_integrity(api)
    except Exception as e:
        await session.close()
        raise e


async def aimodules_integrity(api: NovelAI_API):
    api.timeout = 30

    await api.high_level.login(username, password)

    key = get_encryption_key(username, password)
    keystore = await api.high_level.get_keystore(key)

    modules = await api.high_level.download_user_modules()
    encrypted_modules_in = [str(module) for module in modules]
    decrypt_user_data(modules, keystore)
    encrypt_user_data(modules, keystore)
    encrypted_modules_out = [str(module) for module in modules]

    assert compare_in_out("aimodules", encrypted_modules_in, encrypted_modules_out)

async def test_keystore_integrity_sync():
    # sync handler
    api = NovelAI_API()
    await aimodules_integrity(api)

async def test_keystore_integrity_async():
    # async handler
    try:
        async with ClientSession() as session:
            api = NovelAI_API(session)
            await aimodules_integrity(api)
    except Exception as e:
        await session.close()
        raise e


async def shelves_integrity(api: NovelAI_API):
    api.timeout = 30

    await api.high_level.login(username, password)

    key = get_encryption_key(username, password)

    shelves = await api.high_level.download_user_shelves()
    encrypted_shelves_in = [str(shelf) for shelf in shelves]
    decompress_user_data(shelves)
    compress_user_data(shelves)
    encrypted_shelves_out = [str(shelf) for shelf in shelves]

    assert compare_in_out("shelves", encrypted_shelves_in, encrypted_shelves_out)

async def test_shelves_integrity_sync():
    # sync handler
    api = NovelAI_API()
    await shelves_integrity(api)

async def test_shelves_integrity_async():
    # async handler
    try:
        async with ClientSession() as session:
            api = NovelAI_API(session)
            await shelves_integrity(api)
    except Exception as e:
        await session.close()
        raise e


if __name__ == "__main__":
    async def main():
        await test_keystore_integrity_sync()
        await test_keystore_integrity_async()

        await test_stories_integrity_sync()
        await test_stories_integrity_async()

        await test_storycontent_integrity_sync()
        await test_storycontent_integrity_async()

        await test_presets_integrity_sync()
        await test_presets_integrity_async()

        await test_shelves_integrity_sync()
        await test_shelves_integrity_async()

    run(main())