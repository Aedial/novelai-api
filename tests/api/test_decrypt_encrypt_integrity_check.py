"""
Test if the content decryption/decompression is consistent with encryption/compression for downloaded content
"""

from asyncio import run
from pathlib import Path
from subprocess import PIPE, Popen
from typing import Any, List

from novelai_api import utils
from novelai_api.utils import compress_user_data, decompress_user_data, decrypt_user_data, encrypt_user_data
from tests.api.boilerplate import API, api_handle, api_handle_sync, error_handler  # noqa: F401  # pylint: disable=W0611


def compare_in_out(type_name: str, items_in: List[Any], items_out: List[Any]) -> bool:
    fail_flags = "".join(("O" if item_in == item_out else "X") for item_in, item_out in zip(items_in, items_out))
    if "X" in fail_flags:
        print(f"{fail_flags.count('X')}/{len(fail_flags)} integrity checks failed for {type_name}")
        print(fail_flags)
        print("")

        return False

    print(f"All {len(fail_flags)} integrity checks succeeded for {type_name}\n")
    return True


fflate_path = Path(__file__).parent.absolute() / "fflate_inflate.js"


def inflate_js(data: bytes, _) -> bytes:
    with Popen(["node", fflate_path, str(len(data))], stdin=PIPE, stdout=PIPE) as p:
        out, _ = p.communicate(data)

    return out


@error_handler(wait=0)
async def keystore_integrity(handle: API):
    """
    Verify the integrity of the keystore on decryption - encryption
    """

    api = handle.api
    key = handle.encryption_key

    keystore = await api.high_level.get_keystore(key)

    encrypted_keystore_in = [str(keystore.data)]
    keystore.encrypt(key)
    encrypted_keystore_out = [str(keystore.data)]

    assert compare_in_out("keystore", encrypted_keystore_in, encrypted_keystore_out)


async def test_keystore_integrity_sync(api_handle_sync):  # noqa: F811  # pylint: disable=W0621
    await keystore_integrity(api_handle_sync)


async def test_keystore_integrity_async(api_handle):  # noqa: F811  # pylint: disable=W0621
    await keystore_integrity(api_handle)


@error_handler(wait=0)
async def stories_integrity(handle: API):
    """
    Verify the integrity of 'stories' objects on decryption - encryption
    """

    api = handle.api
    key = handle.encryption_key

    keystore = await api.high_level.get_keystore(key)

    stories = await api.high_level.download_user_stories()
    encrypted_stories_in = [str(story) for story in stories]
    decrypt_user_data(stories, keystore)
    encrypt_user_data(stories, keystore)
    encrypted_stories_out = [str(story) for story in stories]

    assert compare_in_out("stories", encrypted_stories_in, encrypted_stories_out)


async def test_stories_integrity_sync(api_handle_sync):  # noqa: F811  # pylint: disable=W0621
    await stories_integrity(api_handle_sync)


async def test_stories_integrity_async(api_handle):  # noqa: F811  # pylint: disable=W0621
    await stories_integrity(api_handle)


@error_handler(wait=0)
async def storycontent_integrity(handle: API):
    """
    Verify the integrity of 'storycontent' objects on decryption - encryption
    """

    api = handle.api
    key = handle.encryption_key

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


async def test_storycontent_integrity_sync(api_handle_sync):  # noqa: F811  # pylint: disable=W0621
    await storycontent_integrity(api_handle_sync)


async def test_storycontent_integrity_async(api_handle):  # noqa: F811  # pylint: disable=W0621
    await storycontent_integrity(api_handle)


@error_handler(wait=0)
async def presets_integrity(handle: API):
    """
    Verify the integrity of 'presets' objects on decompression - compression
    """

    api = handle.api

    presets = await api.high_level.download_user_presets()
    encrypted_presets_in = [str(preset) for preset in presets]
    decompress_user_data(presets)
    compress_user_data(presets)
    encrypted_presets_out = [str(preset) for preset in presets]

    assert compare_in_out("presets", encrypted_presets_in, encrypted_presets_out)


async def test_presets_integrity_sync(api_handle_sync):  # noqa: F811  # pylint: disable=W0621
    await presets_integrity(api_handle_sync)


async def test_presets_integrity_async(api_handle):  # noqa: F811  # pylint: disable=W0621
    await presets_integrity(api_handle)


@error_handler(wait=0)
async def aimodules_integrity(handle: API):
    """
    Verify the integrity of 'aimodules' objects on decryption - encryption
    """

    api = handle.api
    key = handle.encryption_key

    keystore = await api.high_level.get_keystore(key)

    modules = await api.high_level.download_user_modules()
    encrypted_modules_in = [str(module) for module in modules]
    decrypt_user_data(modules, keystore)
    encrypt_user_data(modules, keystore)
    encrypted_modules_out = [str(module) for module in modules]

    assert compare_in_out("aimodules", encrypted_modules_in, encrypted_modules_out)


async def test_aimodules_integrity_sync(api_handle_sync):  # noqa: F811  # pylint: disable=W0621
    await aimodules_integrity(api_handle_sync)


async def test_aimodules_integrity_async(api_handle):  # noqa: F811  # pylint: disable=W0621
    await aimodules_integrity(api_handle)


@error_handler(wait=0)
async def shelves_integrity(handle: API):
    """
    Verify the integrity of 'shelves' objects on decompression - compression
    """

    api = handle.api

    shelves = await api.high_level.download_user_shelves()
    encrypted_shelves_in = [str(shelf) for shelf in shelves]
    decompress_user_data(shelves)
    compress_user_data(shelves)
    encrypted_shelves_out = [str(shelf) for shelf in shelves]

    assert compare_in_out("shelves", encrypted_shelves_in, encrypted_shelves_out)


async def test_shelves_integrity_sync(api_handle_sync):  # noqa: F811  # pylint: disable=W0621
    await shelves_integrity(api_handle_sync)


async def test_shelves_integrity_async(api_handle):  # noqa: F811  # pylint: disable=W0621
    await shelves_integrity(api_handle)


if __name__ == "__main__":

    async def main():
        async with API() as api:
            await test_keystore_integrity_async(api)
            await test_stories_integrity_async(api)
            await test_storycontent_integrity_async(api)
            await test_presets_integrity_async(api)
            await test_shelves_integrity_async(api)

        async with API(sync=True) as api:
            await test_keystore_integrity_sync(api)
            await test_stories_integrity_sync(api)
            await test_storycontent_integrity_sync(api)
            await test_presets_integrity_sync(api)
            await test_shelves_integrity_sync(api)

    run(main())
