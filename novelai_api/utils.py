from argon2 import hash_password_raw
from argon2 import low_level

from hashlib import blake2b
from base64 import b64encode

def argon_hash(email: str, password: str, size: int, domain: str) -> str:
	data = password[:6] + email + domain

	# salt
	blake = blake2b(digest_size = 16)
	blake.update(data.encode())
	salt = blake.digest()

	# hash
	raw = low_level.hash_secret_raw(password.encode(), salt, 2, int(2000000/1024), 1, size, low_level.Type.ID)
	hashed = b64encode(raw).decode()[:size]

	return hashed

def get_access_key(email: str, password: str):
	return argon_hash(email, password, 64, "novelai_data_access_key").replace('/', '_').replace('+', '-')

def get_encryption_key(email: str, password: str):
	return argon_hash(email, password, 128, "novelai_data_encryption_key")