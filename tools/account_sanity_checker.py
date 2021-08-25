from sys import version_info, path
from os.path import join, abspath, dirname
path.insert(0, abspath(join(dirname(__file__), '..')))

from novelai_api import NovelAI_API
from novelai_api.utils import get_encryption_key, decrypt_user_data, map_meta_to_stories, assign_content_to_story
from aiohttp import ClientSession

from asyncio import run

from typing import List, Tuple, Dict, Any, NoReturn

import json

def check_non_decrypted_item(type_name: str, items: List[Dict[str, Any]]) -> NoReturn:
	failed: List[Tuple[str, str]] = []

	for item in items:
		if item.get("decrypted", False) is False:
			failed.append((item["meta"], item["id"]))

	if failed:
		print(f"{len(failed)}/{len(items)} {type_name} couldn't be decrypted:")
		print(*(f"\tItem {meta} (id = {id})" for meta, id in failed), sep = "\n")
		print("")

filename = join("credentials", "creds_example.txt")
with open(filename) as f:
	username, password = f.read().split(',')

async def main():
	async with ClientSession() as session:
		api = NovelAI_API(session)

		await api.high_level.login(username, password)

		key = get_encryption_key(username, password)
		keystore = await api.high_level.get_keystore(key)

		stories = await api.high_level.download_user_stories()
		decrypt_user_data(stories, keystore)
		check_non_decrypted_item("stories", stories)

		story_contents = await api.high_level.download_user_story_contents()
		decrypt_user_data(story_contents, keystore)
#		print(json.dumps(story_contents, indent = 4))
		check_non_decrypted_item("storycontent", story_contents)

		# FIXME: presets have empty meta, to investigate
#		presets = await api.high_level.download_user_presets()
#		decrypt_user_data(presets, keystore)
#		check_non_decrypted_item("presets", presets)

		modules = await api.high_level.download_user_modules()
		decrypt_user_data(modules, keystore)
		check_non_decrypted_item("aimodules", modules)

run(main())