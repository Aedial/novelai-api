from sys import version_info, path
from os.path import join, abspath, dirname
path.insert(0, abspath(join(dirname(__file__), '..')))

from novelai_api import NovelAI_API
from novelai_api.utils import get_encryption_key, decrypt_user_data, map_meta_to_stories, assign_content_to_story, decompress_user_data
from aiohttp import ClientSession

from asyncio import run
from base64 import b64decode
from random import choice

from typing import List, Tuple, Dict, Set, Any, NoReturn

import json

def check_non_decrypted_item(type_name: str, items: List[Dict[str, Any]]) -> NoReturn:
	failed: List[Tuple[str, str]] = []
	fail_flags: List[str] = []

	for item in items:
		decrypted = item.get("decrypted", False)
		if decrypted is False:
			failed.append((item["meta"], item["id"]))

		fail_flags.append('O' if decrypted else 'X')

	if failed:
		print(f"{len(failed)}/{len(items)} {type_name} couldn't be decrypted: {''.join(fail_flags)}")
		print(*(f"\tItem {id} of meta {meta}" for meta, id in failed), sep = "\n")
		print("")
	else:
		print(f"{len(items)}/{len(items)} {type_name} have been successfully decrypted\n")

def check_duplicate_meta(*args):
	story_and_content_set = sorted(("stories", "storycontent"))

	meta_list: Dict[str, List[Any]] = {}
	item_types: Dict[str, List[Any]] = {}

	# Collect metas
	for items in args:
		for item in items:
			assert "meta" in item
			assert "type" in item

			meta = item["meta"]
			if meta not in meta_list:
				meta_list[meta] = []
				item_types[meta] = []

			meta_list[meta].append(item)
			item_types[meta].append(item["type"])

	# Detect items that have duplicate meta
	for meta in meta_list:
		if meta == "":
			continue

		item_type = item_types[meta]

		if len(item_type) > 1 and sorted(item_type) != story_and_content_set:
			print(f"Duplicate items with meta {meta}:", ", ".join(f"{item['id']} ({item['type']})" for item in meta_list[meta]))

def check_story_content_without_story(stories: List[Dict[str, Any]], story_contents: List[Dict[str, Any]]) -> NoReturn:
	story_metas: Set[str] = set()

	for story in stories:
		assert "meta" in story
		story_metas.add(story["meta"])

	for story_content in story_contents:
		assert "meta" in story_content
		assert "id" in story_content

		if story_content["meta"] not in story_metas:
			print(f"Story content {story_content['id']} of meta {story_content['meta']} does not have an associated story")

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
		decrypt_user_data(stories, keystore)
		check_non_decrypted_item("stories", stories)

		story_contents = await api.high_level.download_user_story_contents()
		decrypt_user_data(story_contents, keystore)
		check_non_decrypted_item("storycontent", story_contents)

		presets = await api.high_level.download_user_presets()
		decompress_user_data(presets)
		check_non_decrypted_item("presets", presets)

		modules = await api.high_level.download_user_modules()
		decrypt_user_data(modules, keystore)
		check_non_decrypted_item("aimodules", modules)

		check_story_content_without_story(stories, story_contents)

		check_duplicate_meta(stories, story_contents, presets, modules)

run(main())