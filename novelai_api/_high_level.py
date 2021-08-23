from novelai_api.NovelAIError import NovelAIError
from novelai_api.utils import get_access_key, get_encryption_key, decrypt_data, encrypt_data

from hashlib import sha256
from typing import Union, Dict, Tuple, List, Any, NoReturn, Optional, MethodDescriptorType
from base64 import b64decode, b64encode

import json
from jsonschema import validate, ValidationError
from os import listdir
from os.path import join, splitext

class High_Level:
	_parent: "NovelAI_API"
	_schemas: Dict[str, Dict[str, Any]] = {}

	def __init__(self, parent: "NovelAI_API"):
		self._parent = parent

		for filename in listdir("schemas"):
			with open(join("schemas", filename)) as f:
				self._schemas[splitext(filename)[0]] = json.loads(f.read())

	async def register(self, recapcha: str, email: str, password: str, send_mail: bool = True, giftkey: Optional[str] = None) -> bool:
		"""
		Register a new account

		:param recapcha: Recapcha of the NovelAI website
		:param email: Email of the account (username)
		:param password: Password of the account
		:param send_mail: Send the mail (hashed and used for recovery)
		:param giftkey: Giftkey

		:return: True if success
		"""

		assert type(email) is str, f"Expected type 'str' for email, but got type '{type(email)}'"
		assert type(password) is str, f"Expected type 'str' for password, but got type '{type(password)}'"

		hashed_email = sha256(email.encode()).hexdigest() if send_mail else None
		key = get_access_key(email, password)
		return await self._parent.low_level.register(recapcha, key, hashed_email, giftkey)

	async def login(self, email: str, password: str) -> Dict[str, str]:
		"""
		Log in to the account

		:param email: Email of the account (username)
		:param password: Password of the account

		:return: True on success
		"""
		assert type(email) is str, f"Expected type 'str' for email, but got type '{type(email)}'"
		assert type(password) is str, f"Expected type 'str' for password, but got type '{type(password)}'"

		access_key = get_access_key(email, password)
		rsp = await self._parent.low_level.login(access_key)
		validate(rsp, self._schemas["schema_login"])

		self._parent._session.headers["Authorization"] = f"Bearer {rsp['accessToken']}"

		return rsp

	async def get_keystore(self, key: bytes) -> Dict[str, Dict[str, bytes]]:
		"""
		Retrieve the keystore and decrypt it in a readable manner.
		The keystore is the mapping of meta -> encryption key of each object.
		If this function throws errors repeatedly at you,
		check your internet connection or the integreity of your keystore.
		Losing your keystore, or overwriting it means losing all content on the account.

		:param key: Account's encryption key
		
		:return: Keystore in the form { "keys": { "<meta>": <key> } }
		"""

		keystore = await self._parent.low_level.get_keystore()
		validate(keystore, self._schemas["schema_keystore_b64"])

		# TODO: check if keystore is actually valid b64 ?

		keystore = json.loads(b64decode(keystore["keystore"]).decode())
		validate(keystore, self._schemas["schema_keystore_encrypted"])

		version = keystore["version"]
		nonce = bytes(keystore["nonce"])
		sdata = bytes(keystore["sdata"])

		data = decrypt_data(sdata, key, nonce)
		json_data = json.loads(data)
		validate(json_data, self._schemas["schema_keystore_decrypted"])

		keys = json_data["keys"]
		for key in keys:
			keys[key] = bytes(keys[key])

		# here, the data should be all valid. Still possible to be false (while valid),
		# but it would be incredibly rare

		json_data["version"] = version
		json_data["nonce"] = nonce

		return json_data

	async def set_keystore(self, keystore: Dict[str, Dict[str, bytes]], key: bytes):
		# FIXME: find what type is 'bytes'
#		validate(keystore, self._schemas["schema_keystore_setter"])

		version = keystore["version"]
		del keystore["version"]
		nonce = keystore["nonce"]
		del keystore["nonce"]

		keys = keystore["keys"]
		for key in keys:
			keys[key] = list(keys[key])

		json_data = json.dumps(keystore)
		encrypted_data = encrypt_data(json_data, key, nonce)

		keystore = {
			"version": version,
			"nonce": list(nonce),
			"sdata": list(encrypted_data)
		}

		keystore = { "keystore": b64encode(json.dumps(keystore)).decode() }

		raise NotImplementedError("This method has not been tested and shouldn't be used. You have been warned")

		self._parent.low_level.set_keystore(keystore)

	async def download_stories(self) -> Dict[str, List[Dict[str, Union[str, int]]]]:
		stories = await self._parent.low_level.download_objects("stories")
		validate(stories, self._schemas["schema_encrypted_stories"])

		return stories["objects"]