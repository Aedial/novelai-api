from novelai_api import NovelAI_API
from nacl.secret import SecretBox

from typing import Dict, List, NoReturn, Any, Optional, Union
from os import urandom
from uuid import uuid4

DEFAULT_MODEL = "6B-v3"
DEFAULT_PARAMS = {
	"temperature": 1,
	"min_lngth": 10,
	"max_length": 30
}

class NovelAI_StoryProxy:
	_parent: "NovelAI_Story"

	_api: NovelAI_API
	_keystore: Dict[str, bytes]
	_key: bytes
	_story: Dict[str, Any]
	model: str
	params: Dict[str, Any]

	def __init__(self, parent: "NovelAI_Story", api: NovelAI_API, key: bytes, story: Dict[str, Any], model: Optional[str] = None, params: Optional[Dict[str, Any]] = None):
		self._parent = parent

		self._api = api
		self._key = key
		self._story = story

		self._model = DEFAULT_MODEL if model is None else model
		self._params = DEFAULT_PARAMS.copy() if params is None else params

	async def generate(self, input: Union[str, List[int]]) -> "NovelAI_StoryProxy":
		output = self._api.low_level.generate(input, self.model, self.params)
		# TODO

	async def undo(self):
		pass

	async def save(self, upload: bool = False):
		pass

	async def choose(self, index: int):
		pass

	async def flatten(self):
		pass

	async def delete(self):
		return self._parent.delete(self._story)

	async def get_current_tree(self):
		pass

class NovelAI_Story:
	_story_instances: List[NovelAI_StoryProxy]

	_api: NovelAI_API
	_keystore: Dict[str, bytes]
	_stories: Dict[str, Dict[str, Any]]

	def __init__(self, api: NovelAI_API, keystore: Dict[str, bytes], stories: Dict[str, Dict[str, Any]]):
		self._api = api
		self._keystore = keystore
		self._stories = stories

	def create(self):
		meta = str(uuid4())
		while meta in self._keystore:
			meta = str(uuid4())

		key = urandom(SecretBox.KEY_SIZE)
		self._keystore[meta] = key

		story = {
			"id": None,
			"meta": meta,
			"data": "",
			"content": [],
			"decrypted": True
		}

		proxy = NovelAI_StoryProxy(self, self._api, key, story)
		self._story_instances.append(proxy)
		return proxy

	def select(self, id: str):
		story = {}	# FIXME

		meta = story["meta"]
		assert meta in self._keystore, "Selected story has no encryption key"
		key = self._keystore[meta]

		proxy = NovelAI_StoryProxy(self, self._api, key, story)
		self._story_instances.append(proxy)		
		return proxy

	def delete(self, story: Dict[str, Any]):
		pass