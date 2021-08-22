from argon2 import hash_password_raw
from argon2 import low_level

from hashlib import blake2b
from base64 import urlsafe_b64encode, b64encode, b64decode
from binascii import b2a_base64

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

def decrypt_stories(stories: Union[List[Dict[str, Any]], Tuple[Dict[str, Any]], Dict[str, Any]], key: bytes, keystore: Dict[str, Dict[str, bytes]]) -> NoReturn:
	"""
	Decrypt the data of each story in :ref: stories
	If a story has already been decrypted, it won't be decrypted a second type

	:param stories: Story or list of stories to decrypt
	"""

	# 1 story
	if type(stories) is not list and type(stories) is not tuple:
		stories = [stories]

	for story in stories:
		assert type(story) is dict, f"Expected type 'dict' for story of 'stories', got type '{type(story)}'"

		if not story.get("decrypted", False):
			# FIXME: replace the assert by meaningful errors ? Expect the data to be right ?
			assert "data" in story, f"Expected key 'data' in story"
			assert "meta" in story, f"Expected key 'meta' in story"

			meta = story["meta"]
			assert meta in keystore["keys"]
			key = keystore["keys"][meta]

			data = decrypt_data(b64decode(story["data"]), key)
			if data is not None:
				story["data"] = data
				story["decrypted"] = True
			else:
				story["decrypted"] = False