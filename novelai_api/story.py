from novelai_api import NovelAI_API
from novelai_api.utils import encrypt_user_data, decrypt_user_data, b64_to_tokens
from novelai_api.Tokenizer import Tokenizer
from novelai_api.Keystore import Keystore
from novelai_api.Idstore import Idstore
from novelai_api.BanList import BanList
from novelai_api.BiasGroup import BiasGroup
from novelai_api.Preset import Preset, Model
from novelai_api.GlobalSettings import GlobalSettings

from copy import deepcopy
from time import time
from json import loads, dumps

from typing import Dict, Iterator, List, NoReturn, Any, Optional, Union, Iterable

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
    TEXT_GENERATION_SETTINGS_VERSION = 2

    DEFAULT_MODEL = Model.Euterpe

    _parent: "NovelAI_Story"

    _api: NovelAI_API
    _key: bytes
    _story: Dict[str, Any]
    _storycontent: Dict[str, Any]
    _tree: List[int]

    banlists: List[BanList]
    biases: List[BiasGroup]
    model: Model
    preset: Preset
    prefix: str
    context_size: int

    def _handle_banlist(self, data: Dict[str, Any]) -> NoReturn:
        if "bannedSequenceGroups" not in data:
            data["bannedSequenceGroups"] = []

        ban_seq = data["bannedSequenceGroups"]
        self.banlists = [BanList(*seq["sequences"], enabled = seq["enabled"]) for seq in ban_seq]

    def _handle_biasgroups(self, data: Dict[str, Any]) -> NoReturn:
        if "phraseBiasGroup" not in data:
            data["phraseBiasGroups"] = []

        self.biases = []
        for bias in data["phraseBiasGroups"]:
            self.biases.append(BiasGroup.from_data(bias))

    def _handle_preset(self, data: Dict[str, Any]) -> NoReturn:
        settings = data["settings"]

        if "textGenerationSettingsVersion" not in settings:
            settings["textGenerationSettingsVersion"] = self.TEXT_GENERATION_SETTINGS_VERSION

        if "prefix" not in settings:
            settings["prefix"] = "vanilla"
        self.prefix = settings["prefix"]

        if "model" not in settings:
            settings["model"] = self.DEFAULT_MODEL.value
        self.model = Model(settings["model"])

        if "preset" not in settings:
            settings["preset"] = ""

        parameters = settings["parameters"]

        if "bad_words_ids" in parameters:
            self.banlists.append(BanList(*parameters["bad_words_ids"]))
            del parameters["bad_words_ids"]

        if "logit_bias_groups" in parameters:
            for bias in parameters["logit_bias_groups"]:
                self.biases.append(BiasGroup.from_data(bias))
            del parameters["logit_bias_groups"]

        self.preset = Preset.from_preset_data(settings)
        self.preset.name = settings["preset"]
        self.preset.model = self.model

    def __init__(self, parent: "NovelAI_Story", key: bytes, story: Dict[str, Any], storycontent: Dict[str, Any]):
        self._parent = parent

        self._api = parent._api
        self._key = key
        self._story = story
        self._storycontent = storycontent
        self._tree = []

        data = storycontent["data"]

        print(dumps(data, indent = 4))
        self._handle_banlist(data)
        self._handle_biasgroups(data)
        self._handle_preset(data)

        # FIXME: variable context size ? From global settings ?
        self.context_size = 2048

        # TODO: trimResponses
        # TODO: banBrackets
        # TODO: dynamicPenaltyRange

        # TODO: remember
        # TODO: AN

        # TODO: Lorebook

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

        cur_block["nextBlock"].append(new_index)

        story["currentBlock"] = new_index
        self._tree.append(new_index)

    def __str__(self) -> str:
        story_fragments = self._storycontent["data"]["story"]["fragments"]

        story_content = "".join(fragment["data"] for fragment in story_fragments)

        # FIXME: handle edit

        return story_content

    def build_context(self) -> List[int]:
        tokens = []

        # TODO: Remember tokens
        # TODO: AN tokens

        # TODO: optimize for large stories ?
        # edit is a pain for input in token form, so we use it's string representation instead
        story_content = str(self)
        story_content_size = self.context_size

        # TODO: add option to remove superfluous spaces at the end

        # only tokenize the tail to handle large stories
        story_tokens = []
        while len(story_tokens) < self.context_size:
            story_content_size *= 2
            story_tokens = Tokenizer.encode(self.model, story_content[-story_content_size:])

            # whole story content is tokenized
            if len(story_content) < story_content_size:
                break

        story_tokens = story_tokens[-self.context_size:]

        # TODO: LB tokens

        # TODO: Order and cut everything to fit

        tokens.extend(story_tokens)

        # Internal assert, should never happen
        assert len(tokens) <= self.context_size

        return tokens

    async def generate(self) -> "NovelAI_StoryProxy":
        input = self.build_context()
        # FIXME: find why the output is garbage
        rsp = await self._api.high_level.generate(input, self.model, self.preset, self._parent.global_settings,
                                                  self.banlists, self.biases, self.prefix)

        output = Tokenizer.decode(self.model, b64_to_tokens(rsp["output"]))
        fragment = { "data": output, "origin": "ai" }

        self._create_datablock(fragment, 0)

    async def edit(self, start: int, end: int, replace: str):
        # FIXME: redo edit implementation

        fragment = { "data": replace, "origin": "edit" }

        self._create_datablock(fragment, end - start)

    async def undo(self):
        story = self._storycontent["data"]["story"]

        cur_index = story["currentBlock"]
        blocks = story["datablocks"]

        cur_block = blocks[cur_index]
        story["currentBlock"] = cur_block["prevBlock"]

    async def redo(self):
        story = self._storycontent["data"]["story"]

        cur_index = story["currentBlock"]
        blocks = story["datablocks"]

        cur_block = blocks[cur_index]
        story["currentBlock"] = cur_block["nextBlock"][-1]

    async def save(self, upload: bool = False) -> bool:
        encrypted_story = encrypt_user_data(deepcopy(self._story), self._parent._keystore)
        encrypted_storycontent = encrypt_user_data(deepcopy(self._storycontent), self._parent._keystore)

        success = True

        # TODO: keep local copy if upload ?
        if upload:
            success = success and await self._api.high_level.upload_user_content(encrypted_storycontent)
            success = success and await self._api.high_level.upload_user_content(encrypted_story)

        return success

    async def choose(self, index: int) -> NoReturn:
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

    async def get_current_tree(self) -> List[Dict[str, Any]]:
        story = self._storycontent["data"]["story"]

        blocks = story["datablocks"]
        return [blocks[i] for i in self._tree]

class NovelAI_Story:
    _story_instances: Dict[str, NovelAI_StoryProxy]

    _api: NovelAI_API
    _keystore: Keystore
    _idstore: Idstore

    global_settings: GlobalSettings

    def __init__(self, api: NovelAI_API, keystore: Keystore, global_settings: GlobalSettings):
        self._api = api
        self._keystore = keystore
        self._idstore = Idstore()

        self.global_settings = global_settings

        self._story_instances = {}

    def __iter__(self) -> Iterator[NovelAI_StoryProxy]:
        return self._story_instances.__iter__()

    def __getitem__(self, story_id: str) -> NovelAI_StoryProxy:
        return self._story_instances[story_id]

    def __len__(self) -> int:
        return len(self._story_instances)

    def load(self, story: Dict[str, Any], storycontent: Dict[str, Any]) -> NovelAI_StoryProxy:
        """
        Load a story proxy from a story and storycontent object
        """
        story_meta = story["meta"]
        story_id = story["data"]["remoteStoryId"]

        assert story_meta == storycontent["meta"], f"Expected meta {story_meta} for storycontent, but got meta {storycontent['meta']}"
        assert story_id == storycontent["id"], f"Missmached id: expected {story_id}, but got {storycontent['id']}"

        proxy = NovelAI_StoryProxy(self, self._keystore[story_meta], story, storycontent)

        # FIXME: ignore or overwrite if id exists ?
        self._story_instances[story_id] = proxy

        return proxy

    def loads(self, stories: Iterable[Dict[str, Any]], storycontents: Iterable[Dict[str, Any]]) -> List[NovelAI_StoryProxy]:
        mapping = {}
        for story in stories:
            if story.get("decrypted"):
                mapping[story["data"]["remoteStoryId"]] = story

        loaded = []
        for storycontent in storycontents:
            if storycontent.get("decrypted"):
                story_id = storycontent["id"]

                if story_id not in mapping:
                    self._api._logger.warn(f"Storycontent {story_id} has no associated story")
                else:
                    proxy = self.load(mapping[story_id], storycontent)
                    del mapping[story_id]

                    loaded.append(proxy)

        for story_id in mapping.keys():
            self._api._logger.warn(f"Story {story_id} has no associated storycontent")

        return loaded

    async def load_from_remote(self) -> List[NovelAI_StoryProxy]:
        stories = await self._api.high_level.download_user_stories()
        storycontents = await self._api.high_level.download_user_story_contents()

        decrypt_user_data(stories, self._keystore)
        decrypt_user_data(storycontents, self._keystore)

        return self.loads(stories, storycontents)

    def create(self) -> NovelAI_StoryProxy:
        meta = self._keystore.create()
        current_time = _get_time()
        current_time_short = _get_short_time()

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

        for path, val in (("id", id_storycontent),
                          ("meta", meta),
                          ("lastUpdatedAt", current_time_short),
                          ("data.contextDefaults.loreDefaults.id", id_lore_default),
                          ("data.contextDefaults.loreDefaults.lastUpdatedAt", current_time)):
            _set_nested_item(storycontent, val, path)


        proxy = self.load(story, storycontent)

        return proxy

    def select(self, story_id: str) -> Optional[NovelAI_StoryProxy]:
        """
        Select a story proxy from the previously created/loaded ones

        :param story_id: Id of the selected story

        :return: Story or None if the story does't exist in the handler
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