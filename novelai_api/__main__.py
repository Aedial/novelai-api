import asyncio
import base64
import inspect
import sys
from argparse import ArgumentParser
from logging import Logger, StreamHandler
from typing import Any, Dict, List, NoReturn, Optional, Set, Tuple

from aiohttp import ClientSession

from novelai_api import NovelAIAPI
from novelai_api.Preset import Model
from novelai_api.Tokenizer import Tokenizer
from novelai_api.utils import decompress_user_data, decrypt_user_data, get_access_key, get_encryption_key


class API:
    """
    Boilerplate for the redundant parts
    """

    _username: str
    _password: str
    _session: ClientSession

    logger: Logger
    api: Optional[NovelAIAPI]

    def __init__(self, username: str, password: str):
        self._username = username
        self._password = password

        self.logger = Logger("NovelAI")
        self.logger.addHandler(StreamHandler())

        self.api = NovelAIAPI(logger=self.logger)
        self.access_token = None

    @property
    def encryption_key(self):
        return get_encryption_key(self._username, self._password)

    async def __aenter__(self):
        self._session = ClientSession()
        await self._session.__aenter__()

        self.api.attach_session(self._session)
        self.access_token = await self.api.high_level.login(self._username, self._password)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._session.__aexit__(exc_type, exc_val, exc_tb)


# access_key
def get_access_key_func(username: str, password: str):
    print(get_access_key(username, password))


# access_token
async def get_access_token_func(username: str, password: str):
    async with API(username, password) as api_handler:
        print(api_handler.access_token)


# sanity_check
def _check_non_decrypted_item(type_name: str, items: List[Dict[str, Any]], logger: Logger) -> NoReturn:
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


def _check_duplicate_meta(*data: List[Dict[str, Any]]):
    story_and_content_set = sorted(("stories", "storycontent"))

    meta_list: Dict[str, List[Any]] = {}
    item_types: Dict[str, List[Any]] = {}

    # Collect metas
    for items in data:
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
    for meta, items in meta_list.items():
        if meta == "":
            continue

        item_type = item_types[meta]

        if len(item_type) > 1 and sorted(item_type) != story_and_content_set:
            ids = ", ".join(f"{item['id']} ({item['type']})" for item in items)
            print(f"Duplicate items with meta {meta}: {ids}")


def _check_story_content_without_story(stories: List[Dict[str, Any]], story_contents: List[Dict[str, Any]]) -> NoReturn:
    story_metas: Set[str] = set()

    for story in stories:
        assert "meta" in story
        story_metas.add(story["meta"])

    for story_content in story_contents:
        assert "meta" in story_content
        assert "id" in story_content

        if story_content["meta"] not in story_metas:
            print(
                f"Story content {story_content['id']} of meta {story_content['meta']} "
                "does not have an associated story"
            )


async def sanity_checker_func(username: str, password: str):
    async with API(username, password) as api_handler:
        api = api_handler.api
        logger = api_handler.logger
        key = api_handler.encryption_key

        keystore = await api.high_level.get_keystore(key)

        stories = await api.high_level.download_user_stories()
        decrypt_user_data(stories, keystore)
        _check_non_decrypted_item("stories", stories, logger)

        story_contents = await api.high_level.download_user_story_contents()
        decrypt_user_data(story_contents, keystore)
        _check_non_decrypted_item("storycontent", story_contents, logger)

        presets = await api.high_level.download_user_presets()
        decompress_user_data(presets)
        _check_non_decrypted_item("presets", presets, logger)

        modules = await api.high_level.download_user_modules()
        decrypt_user_data(modules, keystore)
        _check_non_decrypted_item("aimodules", modules, logger)

        _check_story_content_without_story(stories, story_contents)

        _check_duplicate_meta(stories, story_contents, presets, modules)


# decode
async def decode_func(model: str, data: str):
    model = Model(model)

    tokens = base64.b64decode(data)
    tokens = [int.from_bytes(tokens[i * 2 : (i + 1) * 2], "little") for i in range(len(tokens) // 2)]
    print(f"Tokens = {tokens}")

    text = Tokenizer.decode(model, tokens)
    print(f"Text = {text}")


if __name__ == "__main__":
    parser = ArgumentParser()

    def add_credentials_arguments(p: ArgumentParser):
        p.add_argument("username", help="NovelAI username")
        p.add_argument("password", help="NovelAI password")

    subparser = parser.add_subparsers(help="Function to call")

    # Get access key
    access_key_parser = subparser.add_parser("access_key", help="Get access key")
    access_key_parser.set_defaults(func=get_access_key_func)
    add_credentials_arguments(access_key_parser)

    # Get access token
    access_token_parser = subparser.add_parser("access_token", help="Get access token")
    access_token_parser.set_defaults(func=get_access_token_func)
    add_credentials_arguments(access_token_parser)

    # Sanity check
    sanity_check_parser = subparser.add_parser("sanity_check", help="Sanity check")
    sanity_check_parser.set_defaults(func=sanity_checker_func)
    add_credentials_arguments(sanity_check_parser)

    # Decode
    decode_parser = subparser.add_parser("decode", help="Decode")
    decode_parser.add_argument("model", help="Model to use")
    decode_parser.add_argument("data", help="Data to decode")
    decode_parser.set_defaults(func=decode_func)

    # Parse arguments
    args = parser.parse_args()
    if getattr(args, "func", None) is None:
        parser.print_help()
        sys.exit(1)

    # Get the values of the arguments
    arg_names = inspect.getfullargspec(args.func).args
    args_values = {name: getattr(args, name) for name in arg_names}

    if asyncio.iscoroutinefunction(args.func):
        asyncio.run(args.func(**args_values))
    else:
        args.func(**args_values)
