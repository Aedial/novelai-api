from novelai_api.NovelAIError import NovelAIError
from novelai_api.utils import get_access_key, get_encryption_key

from hashlib import sha256

from base64 import b64decode
import json

from typing import Union, Dict, Tuple, List, Iterable, Any, NoReturn, Optional, MethodDescriptorType

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

	async def get_keystore(self) -> Union[Dict[str, Any], NovelAIError]:
		keystore = await self._parent.low_level.get_keystore()

		# TODO: add enum for error
		if type(keystore) is not dict:
			return NovelAIError(0, f"Expected type 'dict' for get_keystore, but got '{type(keystore)}'")

		if "keystore" not in keystore:
			return NovelAIError(0, f"Expected key 'keystore' in the keystore object")
		
		if type(keystore["keystore"]) is not str:
			return NovelAIError(0, f"Expected type 'str' for the item of keystore, but got '{type(keystore['keystore'])}'")

		try:
			return json.loads(b64decode(keystore["keystore"]).decode())
		except json.JSONDecodeError as e:
			return NovelAIError(0, e.msg)