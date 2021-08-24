from argon2 import hash_password_raw
from argon2 import low_level

from hashlib import blake2b
from base64 import urlsafe_b64encode, b64encode, b64decode
import json

from nacl.secret import SecretBox
from nacl.exceptions import CryptoError

from typing import Dict, Union, List, Tuple, Any, Optional, NoReturn

def argon_hash(email: str, password: str, size: int, domain: str) -> str:
	pre_salt = password[:6] + email + domain

	# salt
	blake = blake2b(digest_size = 16)
	blake.update(pre_salt.encode())
	salt = blake.digest()

	raw = low_level.hash_secret_raw(password.encode(), salt, 2, int(2000000/1024), 1, size, low_level.Type.ID)
	hashed = urlsafe_b64encode(raw).decode()

	return hashed

def get_access_key(email: str, password: str) -> str:
	return argon_hash(email, password, 64, "novelai_data_access_key")[:64]

def get_encryption_key(email: str, password: str) -> bytes:
	pre_key = argon_hash(email, password, 128, "novelai_data_encryption_key")
	pre_key = pre_key.replace('=', '')

	blake = blake2b(digest_size = 32)
	blake.update(pre_key.encode())
	return blake.digest()

def decrypt_data(data: Union[str, bytes], key: bytes, nonce: Optional[bytes] = None) -> Union[str, None]:
	box = SecretBox(key)

	if type(data) is not bytes:
		data = data.encode()

	try:
		return box.decrypt(data, nonce = nonce).decode()
	except CryptoError:
		return None

def encrypt_data(data: Union[str, bytes], key: bytes, nonce: Optional[bytes] = None) -> Union[str, None]:
	box = SecretBox(key)

	if type(data) is not bytes:
		data = data.encode()

	try:
		return box.encrypt(data, nonce = nonce).decode()
	except CryptoError:
		return None

def decrypt_user_data(items: Union[List[Dict[str, Any]]], keystore: Dict[str, Dict[str, bytes]]) -> NoReturn:
	"""
	Decrypt the data of each item in :ref: items
	If a item has already been decrypted, it won't be decrypted a second type

	:param items: Item or list of items to decrypt
	:param keystore: Keystore retrieved with the get_keystore method
	"""

	# 1 item
	if type(items) is not list and type(items) is not tuple:
		items = [items]

	for item in items:
		assert type(item) is dict, f"Expected type 'dict' for item of 'items', got type '{type(item)}'"

		if not item.get("decrypted", False):
			# FIXME: replace the assert by meaningful errors ? Expect the data to be right ?
			assert "data" in item, f"Expected key 'data' in item"
			assert "meta" in item, f"Expected key 'meta' in item"

			meta = item["meta"]
			assert meta in keystore["keys"]
			key = keystore["keys"][meta]

			data = decrypt_data(b64decode(item["data"]), key)
			if data is not None:
				try:
					data = json.loads(data)
					item["data"] = data
					item["decrypted"] = True
				except json.JSONDecodeError:
					item["decrypted"] = False
			else:
				item["decrypted"] = False

def map_meta_to_stories(stories: List[Dict[str, Union[str, int]]]) -> Dict[str, Dict[str, Union[str, int]]]:
	data = {}
	for story in stories:
		data[story["meta"]] = story

	return data

def assign_content_to_story(stories: Dict[str, Dict[str, Union[str, int]]], story_contents: List[Dict[str, Union[str, int]]]) -> NoReturn:
	for story_content in story_contents:
		meta = story_content["meta"]

		if meta in stories and story_content["decrypted"] and stories[meta]["decrypted"]:
			stories[meta]["content"] = story_content

# TODO: story tree builder

# TODO: something to clear the data that couldn't be decrypted from the list ?