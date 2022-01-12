from novelai_api.NovelAIError import NovelAIError
from novelai_api.FakeClientSession import FakeClientSession
from novelai_api.Keystore import Keystore
from novelai_api.SchemaValidator import SchemaValidator
from novelai_api.utils import get_access_key, get_encryption_key, decrypt_data, encrypt_data

from hashlib import sha256
from typing import Union, Dict, Tuple, List, Any, NoReturn, Optional

class High_Level:
	_parent: "NovelAI_API"

	def __init__(self, parent: "NovelAI_API"):
		self._parent = parent

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

	async def login(self, email: str, password: str) -> str:
		"""
		Log in to the account

		:param email: Email of the account (username)
		:param password: Password of the account

		:return: User's access token
		"""
		assert type(email) is str, f"Expected type 'str' for email, but got type '{type(email)}'"
		assert type(password) is str, f"Expected type 'str' for password, but got type '{type(password)}'"

		access_key = get_access_key(email, password)
		rsp = await self._parent.low_level.login(access_key)
		SchemaValidator.validate("schema_login", rsp)

		self._parent._session.headers["Authorization"] = f"Bearer {rsp['accessToken']}"

		return rsp["accessToken"]

	async def login_from_token(self, access_token: str) -> NoReturn:
		self._parent._session.headers["Authorization"] = f"Bearer {access_token}"

	async def get_keystore(self, key: bytes) -> Keystore:
		"""
		Retrieve the keystore and decrypt it in a readable manner.
		The keystore is the mapping of meta -> encryption key of each object.
		If this function throws errors repeatedly at you,
		check your internet connection or the integrity of your keystore.
		Losing your keystore, or overwriting it means losing all content on the account.

		:param key: Account's encryption key
		
		:return: Keystore object
		"""

		keystore = Keystore(await self._parent.low_level.get_keystore())
		keystore.decrypt(key)

		return keystore

	async def set_keystore(self, keystore: Keystore, key: bytes) -> bytes:
		keystore.encrypt(key)

		return await self._parent.low_level.set_keystore(keystore.data)

	async def download_user_stories(self) -> Dict[str, Dict[str, Union[str, int]]]:
		stories = await self._parent.low_level.download_objects("stories")
		SchemaValidator.validate("schema_encrypted_stories", stories)

		return stories["objects"]

	async def download_user_story_contents(self) -> Dict[str, Dict[str, Union[str, int]]]:
		story_contents = await self._parent.low_level.download_objects("storycontent")
		SchemaValidator.validate("schema_encrypted_stories", story_contents)

		return story_contents["objects"]

	async def download_user_presets(self) -> List[Dict[str, Union[str, int]]]:
		presets = await self._parent.low_level.download_objects("presets")
		SchemaValidator.validate("schema_encrypted_stories", presets)

		return presets["objects"]

	async def download_user_modules(self) -> List[Dict[str, Union[str, int]]]:
		modules = await self._parent.low_level.download_objects("aimodules")
		SchemaValidator.validate("schema_encrypted_stories", modules)

		return modules["objects"]

	async def download_user_shelves(self) -> List[Dict[str, Union[str, int]]]:
		modules = await self._parent.low_level.download_objects("shelf")
		SchemaValidator.validate("schema_encrypted_stories", modules)

		return modules["objects"]

	# TODO: encryption and upload