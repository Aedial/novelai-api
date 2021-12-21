from novelai_api import NovelAI_API
from novelai_api.utils import encrypt_user_data

from nacl.secret import SecretBox
from nacl.utils import random

from typing import Dict, List, NoReturn, Any, Optional, Union
from uuid import uuid4
from time import time


DEFAULT_MODEL = "6B-v3"
DEFAULT_PARAMS = {
	"temperature": 1,
	"min_lngth": 10,
	"max_length": 30
}

def get_time() -> int:
	"""
	Get the current time, as formatted for createdAt and lastUpdatedAt

	:return: Current time with millisecond precision
	"""

	return int(time() * 1000)

def get_short_time() -> int:
	"""
	Because some lastUpdatedAt only are precise to the second

	:return: Current time with second precision
	"""

	return int(time())

# FIXME: store the constants, like versions, in a global constants file
def create_new_stories_data(meta: str, current_time: int, current_time_short: int) -> Dict[str, Any]:
	return {
		"id": None,
		"type": "stories",
		"meta": meta,
		"data": {
			"storyMetadatVersion": 1,
			#what to do with id, remoteId, remoteStoryId ?
			"title": "New story",
			"description": "",
			"textPreview": "",
			"favorite": False,
			"tags": [],
			"createdAt": current_time,
			"lastUpdatedAt": current_time,
			"isModified": False
		},
		"lastUpdatedAt": current_time_short,
		"changedIndex": 0,
		"nonce": random(SecretBox.NONCE_SIZE),
		"decrypted": True,
		"compressed": False
	}

def create_new_storycontent_data(meta: str, current_time_short: int) -> Dict[str, Any]:
	return {
		"id": None,
		"storycontent": "storycontent",
		"meta": meta,
		"data": {
			"storyContentVersion": 3,
			"settings": {
				"parameters": {},			# FIXME: default preset ?
				"preset": "",
				"trimResponse": True,
				"banBrackets": True,
				"prefix": ""
			},
			# FIXME: refactor this into a function
			"story": {
				"version": 2,
				"step": 0,
				"datablocks": [ {
					"nextBlock": [],
					"prevBlock": -1,
					"origin": "root",
					"startIndex": 0,
					"endIndex": 0,
					"dataFragment": { "data": "", "origin": "root" },
					"fragmentIndex": -1,
					"removedFragments": [],
					"chain": False
				} ],
				"currentBlock": 0,
				"fragments": [ { "data": "", "origin": "root" } ]
			},
			"context": [
				{
					"text": "",
					"contextConfig": {},		# FIXME: fill me
				},
				{
					"text": "",
					"contextConfig": {},		# FIXME: fill me
				}
			],
			"lorebook": {
				"lorebookVersion": 3,
				"entries": [],
				"settings": { "orderByKeyLocations": False },
				"categories": []
			},
			"storyContextConfig": {},			# FIXME: fill me
			"ephemeralContext": [],
			"contextDefaults": {
				"ephemeralDefaults": [ {} ],	# FIXME: fill me
				"loreDefaults": [ {} ],			# FIXME: fill me
			},
			"settingsDirty": False
		},
		"lastUpdatedAt": current_time_short,
		"changeIndex": 0,
		"decrypted": True,
		"compressed": True
	}

class NovelAI_StoryProxy:
	_parent: "NovelAI_Story"

	_api: NovelAI_API
	_key: bytes
	_story: Dict[str, Any]
	_storycontent: Dict[str, Any]
	model: str

	def __init__(self, parent: "NovelAI_Story", key: bytes, story: Dict[str, Any], storycontent: Dict[str, Any], model: Optional[str] = None):
		self._parent = parent

		self._api = parent._api
		self._key = key
		self._story = story
		self._storycontent = storycontent

		self._model = DEFAULT_MODEL if model is None else model

	async def generate(self, input: Union[str, List[int]]) -> "NovelAI_StoryProxy":
		output = self._api.low_level.generate(input, self.model, self.params)

		story = self._storycontent["data"]["story"]
		blocks = story["datablocks"]
		fragments = story["fragments"]

		cur_index = story["currentBlock"]
		cur_block = blocks[cur_index]

		story["step"] += 1

		fragment = { "data": output, "origin": "" }
		frag_index = len(fragments)
		fragments.append(fragment)

		start = cur_block["endIndex"] + 1
		end = start + len(output)

		block = {
			"nextBlock": [],
			"prevBlock": cur_index,
			"origin": "",
			"startIndex": start,
			"endIndex": end,
			"dataFragment": fragment,
			"fragmentIndex": frag_index,
			"removedFragments": [],
			"chain": False
		}
		new_index = len(blocks)
		blocks.append(block)

		story["currentBlock"] = new_index

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

	async def flatten(self):
		pass

	async def delete(self):
		pass

	async def get_current_tree(self):
		pass

class NovelAI_Story:
	_story_instances: List[NovelAI_StoryProxy]

	_api: NovelAI_API
	_keystore: Dict[str, bytes]
	_stories: Dict[str, Dict[str, Any]]

	def __init__(self, api: NovelAI_API, keystore: Dict[str, bytes]):
		self._api = api
		self._keystore = keystore

	def create(self) -> NovelAI_StoryProxy:
		# FIXME: make a keystore central storage (create, delete, get) to take care of the garbage collection
		meta = str(uuid4())
		while meta in self._keystore:
			meta = str(uuid4())

		key = random(SecretBox.KEY_SIZE)
		self._keystore[meta] = key

		current_time = get_time()
		current_time_short = get_short_time()

		story = create_new_stories_data(meta, current_time, current_time_short)
		storycontent = create_new_storycontent_data(meta, current_time_short)

		proxy = NovelAI_StoryProxy(self, key, story, storycontent)
		self._story_instances.append(proxy)

		return proxy

	def load(self, story, storycontent) -> NovelAI_StoryProxy:
		"""
		Load a story proxy from a story and storycontent object
		"""
		assert story["meta"] == storycontent["meta"], f"Expected meta {story['meta']} for storycontent, but got meta {storycontent['meta']}"

		proxy = NovelAI_StoryProxy(self, self._keystore[story["meta"]], story, storycontent)
		# FIXME: look for duplicates
		self._story_instances.append(proxy)


	def select(self, id: str) -> NovelAI_StoryProxy:
		"""
		Select a story proxy from the previously created/loaded ones
		"""

		# TODO

	def unload(self, id: str):
		"""
		Unload a previously created/loaded story, free'ing the NovelAI_StoryProxy object
		"""