from base64 import b64decode, b64encode
from json import dumps, loads
from typing import Any, Callable, Dict, Optional, Union
from uuid import uuid4

from nacl.secret import SecretBox
from nacl.utils import random

from novelai_api.SchemaValidator import SchemaValidator


class Keystore:
    data: Dict[str, Any]
    _keystore: Optional[Dict[str, bytes]]
    _nonce: bytes
    _version: int

    _decrypted: bool
    _compressed: bool

    # function injection to avoid circular import
    _encrypt_data: Callable
    _decrypt_data: Callable

    def __init__(self, keystore: Union[Dict[str, bytes], None]):
        self.data = keystore
        self._keystore = None
        self._nonce = b""
        self._version = 0

        self._decrypted = False
        self._compressed = False

    def __getitem__(self, key: str) -> bytes:
        if not self._decrypted:
            raise ValueError("Cannot get key from an encrypted keystore")

        return self._keystore[key]

    def __setitem__(self, key: str, val: bytes):
        if not self._decrypted:
            raise ValueError("Cannot set key in an encrypted keystore")

        self._keystore[key] = val

    def __contains__(self, key):
        if not self._decrypted:
            raise ValueError("Cannot find key in an encrypted keystore")

        return key in self._keystore

    def __delitem__(self, key):
        if not self._decrypted:
            raise ValueError("Cannot delete key from an encrypted keystore")

        del self._keystore[key]

    def __len__(self) -> int:
        if not self._decrypted:
            raise ValueError("Cannot get length of an encrypted keystore")

        return len(self._keystore)

    def __str__(self) -> str:
        if not self._decrypted:
            raise ValueError("Cannot show an encrypted keystore")

        return str(self._keystore)

    def create(self) -> str:
        """
        Create a new meta that is not in the keystore and assign a random nonce to it
        """

        if not self._decrypted:
            raise ValueError("Cannot set key in an encrypted keystore")

        meta = next(iter(self._keystore.keys()))
        while meta in self._keystore:
            meta = str(uuid4())

        self._keystore[meta] = random(SecretBox.NONCE_SIZE)

        return meta

    def decrypt(self, key: bytes):
        """
        Decrypt the keystore. The encrypted data should be in Keystore.data

        :param key: Encryption key computed from utils.get_encryption_key()
        """

        keystore = self.data.copy()

        # keystore is empty, create a new one
        if "keystore" in keystore and keystore["keystore"] is None:  # keystore is null when empty
            self._nonce = random(SecretBox.NONCE_SIZE)
            self._version = 2
            self.data = {
                "keystore": {
                    "version": self._version,
                    "nonce": str(list(self._nonce)),
                    "sdata": "",
                }
            }

            self._keystore = {}

            self._compressed = False
            self._decrypted = True

            return

        # keystore is not empty, decrypt it
        keystore = loads(b64decode(self.data["keystore"]).decode())
        SchemaValidator.validate("schema_keystore_encrypted", keystore)

        self._version = keystore["version"]
        self._nonce = bytes(keystore["nonce"])
        sdata = bytes(keystore["sdata"])

        data, _, is_compressed = Keystore._decrypt_data(sdata, key, self._nonce)
        json_data = loads(data)
        SchemaValidator.validate("schema_keystore_decrypted", json_data)

        keys = json_data["keys"]
        for meta in keys:
            keys[meta] = bytes(keys[meta])

        # here, the data should be all valid. Still possible to be false (while valid),
        # but it would be incredibly rare
        self._keystore = keys

        self._compressed = is_compressed
        self._decrypted = True

    def encrypt(self, key: bytes):
        """
        Encrypt a decrypted keystore. The encrypted data will be at Keystore.data

        :param key: Encryption key computed from utils.get_encryption_key()
        """

        # keystore is not decrypted, no need to encrypt it
        if not self._decrypted:
            return

        # FIXME: find what type is 'bytes'
        #        validate(keystore, self._schemas["schema_keystore_setter"])

        if len(self._keystore) == 0:
            keystore = {
                "version": self._version,
                "nonce": list(self._nonce),
                "sdata": "",
            }

        else:
            keystore_bytes = {meta: list(key) for meta, key in self._keystore.items()}
            keys = {"keys": keystore_bytes}

            json_data = dumps(keys, separators=(",", ":"), ensure_ascii=False)
            encrypted_data = Keystore._encrypt_data(json_data, key, self._nonce, self._compressed)
            # remove automatically prepended nonce
            encrypted_data = encrypted_data[SecretBox.NONCE_SIZE :]

            keystore = {
                "version": self._version,
                "nonce": list(self._nonce),
                "sdata": list(encrypted_data),
            }

        keystore_str = dumps(keystore, separators=(",", ":"), ensure_ascii=False)
        self.data["keystore"] = b64encode(keystore_str.encode()).decode()
