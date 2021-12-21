from sys import version_info, path
from os.path import join, abspath, dirname
path.insert(0, abspath(join(dirname(__file__), '..')))

from novelai_api import NovelAI_API
from novelai_api.utils import get_encryption_key, decrypt_user_data, encrypt_user_data, map_meta_to_stories, assign_content_to_story, decompress_user_data, compress_user_data
from aiohttp import ClientSession

from asyncio import run
from base64 import b64decode
from random import choice

from typing import List, Tuple, Dict, Set, Any, NoReturn

import json

def compare_in_out(type_name: str, items_in: List[Dict[str, Any]], items_out: List[Dict[str, Any]]) -> NoReturn:
	fail_flags = ''.join(('O' if item_in == item_out else 'X') for item_in, item_out in zip(items_in, items_out))
	if 'X' in fail_flags:
		print(f"{fail_flags.count('X')}/{len(fail_flags)} integrity checks failed for {type_name}")
		print(fail_flags)
	else:
		print(f"All {len(fail_flags)} integrity checks succeeded for {type_name}")

	print("")

filename = join("credentials", "creds_example.txt")
with open(filename) as f:
	lines = [line.strip() for line in f.readlines()]
	creds = [line for line in lines if line != "" and line[0] != "#"]
	username, password = choice(creds).split(',')

async def main():
	async with ClientSession() as session:
		api = NovelAI_API(session)

		await api.high_level.login(username, password)

		key = get_encryption_key(username, password)
		keystore = await api.high_level.get_keystore(key)

		stories = await api.high_level.download_user_stories()
		encrypted_stories_in = [str(story) for story in stories]
		decrypt_user_data(stories, keystore)
		encrypt_user_data(stories, keystore)
		encrypted_stories_out = [str(story) for story in stories]
		compare_in_out("stories", encrypted_stories_in, encrypted_stories_out)

		story_contents = await api.high_level.download_user_story_contents()
		encrypted_storycontent_in = [str(story_content) for story_content in story_contents]
		decrypt_user_data(story_contents, keystore)
		encrypt_user_data(story_contents, keystore)
		encrypted_storycontent_out = [str(story_content) for story_content in story_contents]
		compare_in_out("storycontent", encrypted_storycontent_in, encrypted_storycontent_out)

		presets = await api.high_level.download_user_presets()
		encrypted_presets_in = [str(preset) for preset in presets]
		decompress_user_data(presets)
		compress_user_data(presets)
		encrypted_presets_out = [str(preset) for preset in presets]
		compare_in_out("presets", encrypted_presets_in, encrypted_presets_out)

		modules = await api.high_level.download_user_modules()
		encrypted_modules_in = [str(module) for module in modules]
		decrypt_user_data(modules, keystore)
		encrypt_user_data(modules, keystore)
		encrypted_modules_out = [str(module) for module in modules]
		compare_in_out("aimodules", encrypted_modules_in, encrypted_modules_out)

run(main())