from sys import path
from os import environ as env
from os.path import join, abspath, dirname

from argparse import ArgumentParser, ArgumentError

path.insert(0, abspath(join(dirname(__file__), '..')))

from novelai_api import NovelAI_API
from novelai_api.utils import get_encryption_key, decrypt_user_data, assign_content_to_story
from aiohttp import ClientSession

from logging import Logger, StreamHandler
from asyncio import run
from json import dumps
from datetime import datetime

from typing import Dict, Any, NoReturn, List, Union

if "NAI_USERNAME" not in env or "NAI_PASSWORD" not in env:
    raise RuntimeError("Please ensure that NAI_USERNAME and NAI_PASSWORD are set in your environment")

username = env["NAI_USERNAME"]
password = env["NAI_PASSWORD"]

logger = Logger("NovelAI")
logger.addHandler(StreamHandler())

def str_to_bool(s: str) -> bool:
    ret = True if s.lower() == "true" else \
          False if s.lower() == "false" else \
          None

    if ret is None:
        raise ArgumentError()

    return ret

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

def match_and_then_or(args: List[List[str]], to_match: Union[str, List[str]]) -> bool:
    return any(all((e in to_match) for e in items) for items in args)

def memory_predicate(args: ArgumentParser, story: Dict[str, Any]) -> bool:
    memory = story["content"]["context"][0]["text"]

    return (args.has_memory is None or args.has_memory is bool(memory)) and \
           (len(args.string_in_memory) == 0 or match_and_then_or(args.string_in_memory, memory))

def an_predicate(args: ArgumentParser, story: Dict[str, Any]) -> bool:
    an = story["content"]["context"][1]["text"]

    return (args.has_an is None or args.has_an is bool(an)) and \
           (len(args.string_in_an) == 0 or match_and_then_or(args.string_in_an, an))

def lorebook_predicate(args: ArgumentParser, story: Dict[str, Any]) -> bool:
    entries = story["content"]["lorebook"]["entries"]
    keys = [key for e in entries for key in e["keys"]]

    return (args.has_lorebook is None or args.has_lorebook is bool(keys)) and \
           (len(args.key_in_lorebook) == 0 or match_and_then_or(args.key_in_lorebook, keys))

PREDICATES = (
    creation_date_predicate,
    update_date_predicate,
#    shelves_predicate,
    memory_predicate,
    an_predicate,
    lorebook_predicate,
)

async def main():
    parser = ArgumentParser(description = "Delete the stories matching all the selected filters, and save them in <backup_directory>. Filters that are not set are ignored")
    parser.add_argument("backup_directory", nargs = "?", default = ".", help = "Directory to save the deleted stories to")

    parser.add_argument("--created-before", type = int, required = False, help = "Select all items created strictly before this time (in ms since Epoch)")
    parser.add_argument("--created-after", type = int, required = False, help = "Select all items created strictly after this time (in ms since Epoch)")
    parser.add_argument("--created-between", type = int, required = False, nargs = 2, default = [], action = "append" , help = "Select all items created strictly between these times (in ms since Epoch)")

    parser.add_argument("--last-updated-before", type = int, required = False, help = "Select all items last updated strictly before this time (in ms since Epoch)")
    parser.add_argument("--last-updated-after", type = int, required = False, help = "Select all items last updated strictly after this time (in ms since Epoch)")
    parser.add_argument("--last-updated-between", type = int, required = False, nargs = 2, default = [], action = "append", help = "Select all items last updated strictly between these times (in ms since Epoch)")

    # TODO: need to query shelves for that
#    parser.add_argument("--exclude-nonshelf", required = False, action = "store_true")
#    parser.add_argument("--included-shelves", type = str, required = False, default = [], nargs = '+', action = "extend")

    parser.add_argument("--has-memory", type = str_to_bool, required = False, help = "Select all items having text in Memory or not")
    parser.add_argument("--string-in-memory", type = str, required = False, default = [], nargs = '+', action = "append", help = "Select all items having the specified text in Memory. Text in the same argument are AND, text on a different argument are OR.")

    parser.add_argument("--has-an", type = str_to_bool, required = False, help = "Select all items having text in A/N or not")
    parser.add_argument("--string-in-an", type = str, required = False, default = [], nargs = '+', action = "append", help = "Select all items having the specified text in A/N. Text in the same argument are AND, text on a different argument are OR.")

    parser.add_argument("--has-lorebook", type = str_to_bool, required = False, help = "Select all items having a Lorebook or not")
    parser.add_argument("--key-in-lorebook", type = str, required = False, default = [], nargs = '+', action = "append", help = "Select all items having the specified keys in Lorebook. Keys in the same argument are AND, keys on a different argument are OR.")

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
                    await api.low_level.delete_object("stories", story_id)

                    storycontent_id = story["content"]["id"]
                    await api.low_level.delete_object("storycontent", storycontent_id)

run(main())