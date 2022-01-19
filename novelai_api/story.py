from novelai_api import NovelAI_API
from novelai_api.utils import encrypt_user_data
from novelai_api.Keystore import Keystore
from novelai_api.Idstore import Idstore

from nacl.secret import SecretBox
from nacl.utils import random

from typing import Dict, List, NoReturn, Any, Optional, Union
from uuid import uuid4
from time import time
from json import loads


def _get_time() -> int:
    """
    Get the current time, as formatted for createdAt and lastUpdatedAt

    :return: Current time with millisecond precision
    """

    return int(time() * 1000)

def _get_short_time() -> int:
    """
    Because some lastUpdatedAt only are precise to the second

    :return: Current time with second precision
    """

    return int(time())

def _set_nested_item(item: Dict[str, Any], val: Any, path: str):
    path = path.split('.')

    for key in path[:-1]:
        item = item[key]

    item[path[-1]] = val

class NovelAI_StoryProxy:
    _parent: "NovelAI_Story"

    _api: NovelAI_API
    _key: bytes
    _story: Dict[str, Any]
    _storycontent: Dict[str, Any]
    _tree: List[int]

    def __init__(self, parent: "NovelAI_Story", key: bytes, story: Dict[str, Any], storycontent: Dict[str, Any], model: Optional[str] = None):
        self._parent = parent

        self._api = parent._api
        self._key = key
        self._story = story
        self._storycontent = storycontent
        self._tree = []

        self._model = DEFAULT_MODEL if model is None else model

    def _create_datablock(self, fragment: Dict[str, str], end_offset: int):
        story = self._storycontent["data"]["story"]
        blocks = story["datablocks"]
        fragments = story["fragments"]

        cur_index = story["currentBlock"]
        cur_block = blocks[cur_index]

        story["step"] += 1

        frag_index = len(fragments)
        fragments.append(fragment)

        start = cur_block["endIndex"] + len(cur_block["dataFragment"]["data"])

        block = {
            "nextBlock": [],
            "prevBlock": cur_index,
            "origin": fragment["origin"],
            "startIndex": start,
            "endIndex": start + end_offset,
            "dataFragment": fragment,
            "fragmentIndex": frag_index,
            "removedFragments": [],
            "chain": False
        }
        new_index = len(blocks)
        blocks.append(block)

        story["currentBlock"] = new_index
        self._tree.append(new_index)

    async def generate(self, input: Union[str, List[int]]) -> "NovelAI_StoryProxy":
        output = await self._api.low_level.generate(input, self.model, self.params)
        fragment = { "data": output, "origin": "ai" }

        self._create_datablock(fragment, 0)

    async def edit(self, start: int, end: int, replace: str):
        fragment = { "data": replace, "origin": "edit" }

        self._create_datablock(fragment, end - start)

    async def undo(self):
        story = self._storycontent["data"]["story"]

        cur_index = story["currentBlock"]
        blocks = story["datablocks"]
    
        cur_block = blocks[cur_index]
        story["currentBlock"] = cur_block["prevBlock"]

    async def save(self, upload: bool = False):
        encrypted_story = encrypt_user_data(self._story)
        encrypted_storycontent = encrypt_user_data(self._storycontent)
        # TODO

    async def choose(self, index: int):
        story = self._storycontent["data"]["story"]

        cur_index = story["currentBlock"]
        blocks = story["datablocks"]
    
        cur_block = blocks[cur_index]
        next_blocks = cur_block["nextBlock"]
        assert 0 <= index < len(next_blocks), f"Expected index between 0 and {len(next_blocks)}, but got {index}"

        story["currentBlock"] = next_blocks[index]

    async def flatten(self) -> NoReturn:
        story = self._storycontent["data"]["story"]

        blocks = story["datablocks"]
        new_datablocks = [blocks[i] for i in self._tree]
        self._tree = [i for i in range(len(new_datablocks))]
        story["datablocks"] = new_datablocks

    async def delete(self):
        pass

    async def get_current_tree(self):
        story = self._storycontent["data"]["story"]

        blocks = story["datablocks"]
        return [blocks[i] for i in self._tree]

class NovelAI_Story:
    _story_instances: Dict[str, NovelAI_StoryProxy]

    _api: NovelAI_API
    _keystore: Keystore
    _idstore: Idstore

    def __init__(self, api: NovelAI_API, keystore: Keystore, idstore: Idstore):
        self._api = api
        self._keystore = keystore
        self._idstore = Idstore()

        self._story_instances = {}

    def create(self) -> NovelAI_StoryProxy:
        meta = self._keystore.create()
        current_time = get_time()
        current_time_short = get_short_time()

        with open("templates/template_empty_story.txt") as f:
            story = loads(f.read())

        # local overwrites
        id_story = self._idstore.create()
        for path, val in (("id", id_story),
                          ("meta", meta),
                          ("data.id", meta),
                          ("data.remoteStoryId", id_story),
                          ("data.createdAt", current_time),
                          ("data.lastUpdatedAt", current_time),
                          ("lastUpdatedAt", current_time_short)):
            _set_nested_item(story, val, path)

        with open("templates/template_empty_storycontent.txt") as f:
            storycontent = loads(f.read())

        # local overwrites
        id_storycontent = self._idstore.create()
        id_lore_default = ""    # FIXME: get id

        for path, val in (("id", storycontent_id),
                          ("meta", meta),
                          ("lastUpdatedAt", current_time_short),
                          ("data.contextDefaults.loreDefaults.id", id_lore_default),
                          ("data.contextDefaults.loreDefaults.lastUpdatedAt", current_time)):
            _set_nested_item(storycontent, val, path)


        proxy = self.load(story, storycontent)

        return proxy

    def load(self, story: Dict[str, Any], storycontent: Dict[str, Any]) -> NovelAI_StoryProxy:
        """
        Load a story proxy from a story and storycontent object
        """
        story_meta = story["meta"]
        story_id = story["data"]["remoteStoryId"]

        assert story_meta == storycontent["meta"], f"Expected meta {story_meta} for storycontent, but got meta {storycontent['meta']}"
        assert story_id == storycontent["id"], f"Missmached id: expected {story_id}, but got {storycontent['id']}"

        proxy = NovelAI_StoryProxy(self, self._keystore[story["meta"]], story, storycontent)

        # FIXME: ignore or overwrite if id exists ?
        self._story_instances[story_id] = proxy

        return proxy

    def loads(self, stories: Iterable[Dict[str, Any]], storycontents: Iterable[Dict[str, Any]]) -> List[NovelAI_StoryProxy]:
        mapping = { }

        for story in stories:
            mapping[story["remoteStoryId"]] = { "story": story }

        for storycontent in storycontents:
            story_id = storycontent["id"]

            if story_id not in mapping:
                self._api._logger.warn(f"Storycontent {story_id} has no associated story")
            else:
                mapping[story_id]["content"] = storycontent

        loaded = []
        for story_id, item in mapping.items():
            if "content" not in item:
               self._api._logger.warn(f"Story {story_id} has no associated storycontent")
            else:
                story = item["story"]
                content = item["content"]
                proxy = self.load(story, content)

                loaded.append(proxy)

        return loaded

    def select(self, story_id: str) -> Optional[NovelAI_StoryProxy]:
        """
        Select a story proxy from the previously created/loaded ones
        """

        if story_id not in self._story_instances:
            return None

        return self._story_instances[story_id]

    def unload(self, story_id: str) -> NoReturn:
        """
        Unload a previously created/loaded story, free'ing the NovelAI_StoryProxy object
        """

        if story_id in self._story_instances:
            del self._story_instances[story_id]