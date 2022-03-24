from sys import path
from os import environ as env
from os.path import join, abspath, dirname

from argparse import ArgumentParser

path.insert(0, abspath(join(dirname(__file__), '..')))

from novelai_api import NovelAI_API
from novelai_api.utils import get_encryption_key, decrypt_user_data, assign_content_to_story
from aiohttp import ClientSession

from logging import Logger, StreamHandler
from asyncio import run
from json import dumps
from datetime import datetime

from typing import Dict, Any, NoReturn

if "NAI_USERNAME" not in env or "NAI_PASSWORD" not in env:
    raise RuntimeError("Please ensure that NAI_USERNAME and NAI_PASSWORD are set in your environment")

username = env["NAI_USERNAME"]
password = env["NAI_PASSWORD"]

logger = Logger("NovelAI")
logger.addHandler(StreamHandler())

def save_story(i: int, story: Dict[str, Any], args: ArgumentParser) -> NoReturn:
    name = story["metadata"]["title"]
    path = join(args.backup_directory, f"{i}-{name}.scenario")

    # remove useless keys
    del story["metadata"]["remoteStoryId"]
    if "remoteId" in story["metadata"]:
        del story["metadata"]["remoteId"]

    with open(path, "w") as f:
        f.write(dumps(story, ensure_ascii = False, indent = 2))

def creation_date_predicate(args: ArgumentParser, story: Dict[str, Any]) -> bool:
    creation_date = story["metadata"]["createdAt"]

    return (args.created_before is None or creation_date < args.created_before) and \
           (args.created_after is None or args.created_after < creation_date) and \
           all(date[0] < creation_date < date[1] for date in args.created_between)

def update_date_predicate(args: ArgumentParser, story: Dict[str, Any]) -> bool:
    update_date = story["metadata"]["lastUpdatedAt"]

    return (args.last_updated_before is None or update_date < args.last_updated_before) and \
           (args.last_updated_after is None or args.last_updated_after < update_date) and \
           all(date[0] < update_date < date[1] for date in args.last_updated_between)

def shelves_predicate(args: ArgumentParser, story: Dict[str, Any]) -> bool:
    # FIXME: need to import shelves, isn't it ?
    shelf = None

    return (args.exclude_nonshelf ^ (shelf is None)) and \
           (shelf is None or shelf in args.included_shelves)

def memory_predicate(args: ArgumentParser, story: Dict[str, Any]) -> bool:
    memory = story["content"]["context"][0]["text"]

    return (args.has_memory is None or args.has_memory is bool(memory)) and \
           (len(args.string_in_memory) == 0 or any(s in memory for s in args.string_in_memory))

def an_predicate(args: ArgumentParser, story: Dict[str, Any]) -> bool:
    an = story["content"]["context"][1]["text"]

    return (args.has_an is None or args.has_an is bool(an)) and \
           (len(args.string_in_an) == 0 or any(s in memory for s in args.string_in_an))

def lorebook_predicate(args: ArgumentParser, story: Dict[str, Any]) -> bool:
    lorebook = story["content"]["lorebook"]["entries"]

    return (args.has_lorebook is None or args.has_lorebook is bool(lorebook)) and \
           (len(args.keys_in_lorebook) == 0 or any(key in args.keys_in_lorebook for e in lorebook for key in e["keys"]))

PREDICATES = (
    creation_date_predicate,
    update_date_predicate,
#    shelves_predicate,
    memory_predicate,
    an_predicate,
    lorebook_predicate,
)

async def main():
    parser = ArgumentParser()
    parser.add_argument("backup_directory", nargs = "?", default = ".", help = "Directory to save the deleted stories to")

    parser.add_argument("--created-before", type = int, required = False)
    parser.add_argument("--created-after", type = int, required = False)
    parser.add_argument("--created-between", type = int, required = False, nargs = 2, default = [], action = "append")

    parser.add_argument("--last-updated-before", required = False)
    parser.add_argument("--last-updated-after", required = False)
    parser.add_argument("--last-updated-between", required = False, nargs = 2, default = [], action = "append")

#    parser.add_argument("--exclude-nonshelf", required = False, action = "store_true")
#    parser.add_argument("--included-shelves", type = str, required = False, default = [], nargs = '+')

    parser.add_argument("--has-memory", type = bool, required = False)
    parser.add_argument("--string-in-memory", type = str, required = False, default = [], nargs = '+')

    parser.add_argument("--has-an", type = bool, required = False)
    parser.add_argument("--string-in-an", type = str, required = False, default = [], nargs = '+')

    parser.add_argument("--has-lorebook", type = bool, required = False)
    parser.add_argument("--keys-in-lorebook", type = str, required = False, default = [], nargs = '+')

    args = parser.parse_args()
    print(vars(args))

    async with ClientSession() as session:
        api = NovelAI_API(session, logger = logger)

        login = await api.high_level.login(username, password)

        key = get_encryption_key(username, password)
        keystore = await api.high_level.get_keystore(key)

        stories = await api.high_level.download_user_stories()
        decrypt_user_data(stories, keystore)

        story_contents = await api.high_level.download_user_story_contents()
        decrypt_user_data(story_contents, keystore)

        assign_content_to_story(stories, story_contents)

        for i, story in enumerate(stories):
            if story.get("decrypted") and "content" in story:
                content = {"storyContainerVersion": 1}
                content["metadata"] = story["data"]
                content["content"] = story["content"]["data"]

                if all(predicate(args, content) for predicate in PREDICATES):
#                    print(i, content["metadata"]["title"])
                    save_story(i, content, args)

                    story_id = story["id"]
#                    api.low_level.delete_object("stories", story_id)

                    storycontent_id = story["content"]["id"]
#                    api.low_level.delete_object("storycontent", storycontent_id)

run(main())