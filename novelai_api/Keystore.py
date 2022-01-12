from typing import Dict, NoReturn, Union, Callable

from uuid import uuid4
from jsonschema import validate
from json import loads, dumps
from base64 import b64decode, b64encode

from nacl.utils import random
from nacl.secret import SecretBox

from novelai_api.SchemaValidator import SchemaValidator

class Keystore:
    data: Dict[str, str]
    _keystore: Dict[str, bytes]
    _nonce: bytes
    _version: int

    _decrypted: bool
    _compressed: bool


    # function insertion to avoid circular import
    _encrypt_data: Callable
    _decrypt_data: Callable

    def __init__(self, keystore: Union[Dict[str, bytes], None]):
        self.data = keystore
        self._keystore = None
        self._nonce = b''
        self._version = 0

        self._decrypted = False
        self._compressed = False

    def __getitem__(self, key: str) -> bytes:
        assert self._decrypted, "Can't get key from an encrypted keystore"
        return self._keystore[key]

    def __setitem__(self, key: str, val: bytes) -> NoReturn:
        assert self._decrypted, "Can't set meta in an encrypted keystore"
        self._keystore[key] = val

    def __contains__(self, key):
        assert self._decrypted, "Can't set meta in an encrypted keystore"
        return key in self._keystore

    def __delitem__(self, key):
        assert self._decrypted, "Can't set meta in an encrypted keystore"
        del self._keystore[key]

    def __len__(self) -> int:
        assert self._decrypted, "Can't set meta in an encrypted keystore"
        return len(self._keystore)

    def __str__(self) -> str:
        assert self._decrypted, "Can't set meta in an encrypted keystore"
        return str(self._keystore)

    def create(self) -> str:
        assert self._decrypted, "Can't set key in an encrypted keystore"
        meta = self._keystore.keys()[0]
        while meta in self._keystore:
            meta = uuid4()

        self._keystore[meta] = random(SecretBox.NONCE_SIZE)

        return meta

    def decrypt(self, key: bytes) -> NoReturn:
        keystore = self.data.copy()

        if "keystore" in keystore and keystore["keystore"] is None:    # keystore is null when empty
            self.data = {
                keystore: {
                    "version": 2,
                    "nonce": str(list(random(SecretBox.NONCE_SIZE))),
                    "sdata": ""
                }
            }

            self._keystore = { }

            self._compressed = False
            self._decrypted = True

            return

        SchemaValidator.validate("schema_keystore_b64", self.data)

        # TODO: check if keystore is actually valid b64 ?

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

    def encrypt(self, key: bytes) -> NoReturn:
        # FIXME: find what type is 'bytes'
#        validate(keystore, self._schemas["schema_keystore_setter"])

        keystore = self._keystore.copy()
        for meta in keystore:
            keystore[meta] = list(keystore[meta])

        keys = { "keys": keystore }
        json_data = dumps(keys, separators = (',', ':'))
        encrypted_data = Keystore._encrypt_data(json_data, key, self._nonce, self._compressed)

        keystore = {
            "version": self._version,
            "nonce": list(self._nonce),
            "sdata": list(encrypted_data)
        }

        self.data["keystore"] = b64encode(dumps(keystore, separators = (',', ':')).encode()).decode()