from boilerplate import API
from novelai_api.utils import decrypt_user_data, decompress_user_data

from logging import Logger
from asyncio import run

from typing import List, Tuple, Dict, Set, Any, NoReturn


def check_non_decrypted_item(type_name: str, items: List[Dict[str, Any]], logger: Logger) -> NoReturn:
    failed: List[Tuple[str, str]] = []
    fail_flags: List[str] = []

    for item in items:
        decrypted = item.get("decrypted", False)
        if decrypted is False:
            failed.append((item["meta"], item["id"]))

        fail_flags.append("O" if decrypted else "X")

    if failed:
        logger.info(f"{len(failed)}/{len(items)} {type_name} couldn't be decrypted: {''.join(fail_flags)}")
        logger.info("\n".join(f"\tItem {id} of meta {meta}" for meta, id in failed))
        logger.info("")
    else:
        logger.info(f"{len(items)}/{len(items)} {type_name} have been successfully decrypted\n")


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
            ids = ", ".join(f"{item['id']} ({item['type']})" for item in meta_list[meta])
            print(f"Duplicate items with meta {meta}: {ids}")


def check_story_content_without_story(stories: List[Dict[str, Any]], story_contents: List[Dict[str, Any]]) -> NoReturn:
    story_metas: Set[str] = set()

    for story in stories:
        assert "meta" in story
        story_metas.add(story["meta"])

    for story_content in story_contents:
        assert "meta" in story_content
        assert "id" in story_content

        if story_content["meta"] not in story_metas:
            print(
                f"Story content {story_content['id']} of meta {story_content['meta']} does not have an associated story"
            )


async def main():
    async with API() as api_handler:
        api = api_handler.api
        logger = api_handler.logger
        key = api_handler.encryption_key

        keystore = await api.high_level.get_keystore(key)

        stories = await api.high_level.download_user_stories()
        decrypt_user_data(stories, keystore)
        check_non_decrypted_item("stories", stories, logger)

        story_contents = await api.high_level.download_user_story_contents()
        decrypt_user_data(story_contents, keystore)
        check_non_decrypted_item("storycontent", story_contents, logger)

        presets = await api.high_level.download_user_presets()
        decompress_user_data(presets)
        check_non_decrypted_item("presets", presets, logger)

        modules = await api.high_level.download_user_modules()
        decrypt_user_data(modules, keystore)
        check_non_decrypted_item("aimodules", modules, logger)

        check_story_content_without_story(stories, story_contents)

        check_duplicate_meta(stories, story_contents, presets, modules)


run(main())
