from novelai_api.NovelAIError import NovelAIError
from novelai_api.utils import get_access_key, get_encryption_key, decrypt_data

from hashlib import sha256

from base64 import b64decode, b64encode
import json

from typing import Union, Dict, Tuple, List, Any, NoReturn, Optional, MethodDescriptorType

class High_Level:
	_parent: "NovelAI_API"

	def __init__(self, parent: "NovelAI_API"):
		self._parent = parent

	async def register(self, recapcha: str, email: str, password: str, send_mail: bool = True, giftkey: Optional[str] = None) -> Union[bool, NovelAIError]:
		"""
		Register a new account

		:param recapcha: Recapcha of the NovelAI website
		:param email: Email of the account (username)
		:param password: Password of the account
		:param send_mail: Send the mail (hashed and used for recovery)
		:param giftkey: Giftkey

		:return: True if success, NovelAIError otherwise
		"""

		assert type(email) is str, f"Expected type 'str' for email, but got type '{type(email)}'"
		assert type(password) is str, f"Expected type 'str' for password, but got type '{type(password)}'"

		hashed_email = sha256(email.encode()).hexdigest() if send_mail else None
		key = get_access_key(email, password)
		return await self._parent.low_level.register(recapcha, key, hashed_email, giftkey)

	async def login(self, email: str, password: str) -> Union[Dict[str, str], NovelAIError]:
		"""
		Log in to the account

		:param email: Email of the account (username)
		:param password: Password of the account

		:return: True on success, NovelAIError otherwise
		"""
		assert type(email) is str, f"Expected type 'str' for email, but got type '{type(email)}'"
		assert type(password) is str, f"Expected type 'str' for password, but got type '{type(password)}'"

		access_key = get_access_key(email, password)
		return await self._parent.low_level.login(access_key)

	async def get_keystore(self, key: bytes) -> Union[Dict[str, Any], NovelAIError]:
		keystore = await self._parent.low_level.get_keystore()

		# TODO: add enum for error
		if type(keystore) is not dict:
			return NovelAIError(0, f"Expected type 'dict' for get_keystore, but got '{type(keystore)}'")

		if "keystore" not in keystore:
			return NovelAIError(0, f"Expected key 'keystore' in the keystore object")
		
		if type(keystore["keystore"]) is not str:
			return NovelAIError(0, f"Expected type 'str' for the item of keystore, but got '{type(keystore['keystore'])}'")

		try:
			keystore = json.loads(b64decode(keystore["keystore"]).decode())
		except json.JSONDecodeError as e:
			return NovelAIError(0, e.msg)

		if "nonce" not in keystore:
			return NovelAIError(0, f"Expected key 'nonce' in the keystore object")			

		if "sdata" not in keystore:
			return NovelAIError(0, f"Expected key 'sdata' in the keystore object")

		nonce = bytes(keystore["nonce"])
		sdata = bytes(keystore["sdata"])

		data = decrypt_data(sdata, key, nonce)
		if data is None:
			return NovelAIError(0, "Failed to decrypt keystore")

		try:
			json_data = json.loads(data)
		except json.JSONDecodeError as e:
			return NovelAIError(0, e.msg)

		if "keys" not in json_data:
			NovelAIError(0, "Expected key 'keys' in the decrypted keystore")

		keys = json_data["keys"]

		if type(keys) is not dict:
			return NovelAIError(0, "Invalid keys in decrypted keystore")

		for key in keys:
			if type(key) is not str:
				return NovelAIError(0, "Invalid item in decrypted keystore")

			if type(keys[key]) is not list:
				return NovelAIError(0, "Invalid item in decrypted keystore")

			keys[key] = bytes(keys[key])

		# here, the data should be all valid

		return json_data

	async def download_stories(self) -> Union[Dict[str, List[Dict[str, Union[str, int]]]], NovelAIError]:
		stories = await self._parent.low_level.download_objects("stories")

		# TODO: add enum for error
		if type(stories) is not dict:
			return NovelAIError(0, f"Expected type 'dict' for stories, but got '{type(stories)}'")

		if "objects" not in stories:
			return NovelAIError(0, f"Expected key 'objects' in the stories object")

		if type(stories["objects"]) is not list:
			return NovelAIError(0, f"Expected type 'list' for the item of stories, but got '{type(stories['objects'])}'")

		for story in stories["objects"]:
			assert type(story) is dict, f"Expected type 'dict' for the items in stories, but got '{type(story)}'"
			story["decrypted"] = False

		return stories["objects"]