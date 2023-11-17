import json
from base64 import b64decode, b64encode, urlsafe_b64encode
from hashlib import blake2b
from typing import Any, AsyncGenerator, AsyncIterable, Dict, Iterable, List, Optional, Tuple, Union
from zlib import MAX_WBITS, Z_BEST_COMPRESSION
from zlib import compressobj as deflate_obj
from zlib import decompress as inflate

import argon2
from nacl.exceptions import CryptoError
from nacl.secret import SecretBox

from novelai_api.Keystore import Keystore
from novelai_api.NovelAIError import NovelAIError
from novelai_api.Preset import Model, Preset
from novelai_api.python_utils import assert_type
from novelai_api.Tokenizer import Tokenizer


# API utils
def argon_hash(email: str, password: str, size: int, domain: str) -> str:
    pre_salt = f"{password[:6]}{email}{domain}"

    # salt
    blake = blake2b(digest_size=16)
    blake.update(pre_salt.encode())
    salt = blake.digest()

    raw = argon2.low_level.hash_secret_raw(
        password.encode(),
        salt,
        2,
        int(2000000 / 1024),
        1,
        size,
        argon2.low_level.Type.ID,
    )
    hashed = urlsafe_b64encode(raw).decode()

    return hashed


def get_access_key(email: str, password: str) -> str:
    assert_type(str, email=email, password=password)

    return argon_hash(email, password, 64, "novelai_data_access_key")[:64]


def get_encryption_key(email: str, password: str) -> bytes:
    assert_type(str, email=email, password=password)

    pre_key = argon_hash(email, password, 128, "novelai_data_encryption_key").replace("=", "")

    blake = blake2b(digest_size=32)
    blake.update(pre_key.encode())

    return blake.digest()


COMPRESSION_PREFIX = b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01"


def decrypt_data(
    data: Union[str, bytes], key: bytes, nonce: Optional[bytes] = None
) -> Union[Tuple[str, bytes, bool], Tuple[None, None, bool]]:
    box = SecretBox(key)

    if not isinstance(data, bytes):
        data = data.encode()

    # data is compressed
    is_compressed = data.startswith(COMPRESSION_PREFIX)
    if is_compressed:
        data = data[len(COMPRESSION_PREFIX) :]

    if nonce is None:
        nonce = data[: box.NONCE_SIZE]
        data = data[box.NONCE_SIZE :]

    try:
        data = box.decrypt(data, nonce=nonce)
        if is_compressed:
            data = inflate(data, -MAX_WBITS)

        return data.decode(), nonce, is_compressed
    except CryptoError:
        return None, None, False


def encrypt_data(
    data: Union[str, bytes],
    key: bytes,
    nonce: Optional[bytes] = None,
    is_compressed: bool = False,
) -> bytes:
    box = SecretBox(key)

    if not isinstance(data, bytes):
        data = data.encode()

    # NOTE: zlib results in different data than the library used by NAI, but they are fully compatible
    if is_compressed:
        deflater = deflate_obj(Z_BEST_COMPRESSION, wbits=-MAX_WBITS)
        data = deflater.compress(data) + deflater.flush()

    data = bytes(box.encrypt(data, nonce))

    if is_compressed:
        data = COMPRESSION_PREFIX + data

    return data


# function injection to avoid circular import
if not hasattr(Keystore, "_encrypt_data"):
    Keystore._encrypt_data = encrypt_data

if not hasattr(Keystore, "_decrypt_data"):
    Keystore._decrypt_data = decrypt_data


def decompress_user_data(items: Union[List[Dict[str, Any]], Dict[str, Any]]):
    """
    Decompress the data of each item in :ref: items
    Doesn't decrypt, but does a b64 to UTF8 translation
    """

    if not isinstance(items, (list, tuple)):
        items = [items]

    for i, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"Expected type 'dict' for item #{i} of 'items', got type '{type(item)}'")
        if "data" not in item:
            raise ValueError(f"Expected key 'data' in item #{i} of 'items'")

        # skip already decompressed data
        if item.get("decrypted"):
            continue

        try:
            data = b64decode(item["data"])

            is_compressed = data.startswith(COMPRESSION_PREFIX)
            if is_compressed:
                data = data[len(COMPRESSION_PREFIX) :]
                data = inflate(data, -MAX_WBITS)

            item["data"] = json.loads(data.decode())
            item["decrypted"] = True  # not decrypted, per se, but for genericity
            item["compressed"] = is_compressed
        except json.JSONDecodeError:
            item["decrypted"] = False


def compress_user_data(items: Union[List[Dict[str, Any]], Dict[str, Any]]):
    """
    Compress the data of each item in :ref: items
    Doesn't encrypt, but does a UTF8 to b64 translation
    Must have been decompressed by decompress_user_data()
    """

    if not isinstance(items, (list, tuple)):
        items = [items]

    for i, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"Expected type 'dict' for item #{i} of 'items', got type '{type(item)}'")

        if "data" not in item:
            raise ValueError(f"Expected key 'data' in item #{i} of 'items'")

        if "decrypted" in item:
            if item["decrypted"]:
                data = json.dumps(item["data"], separators=(",", ":"), ensure_ascii=False).encode()

                if "compressed" in item:
                    if item["compressed"]:
                        deflater = deflate_obj(Z_BEST_COMPRESSION, wbits=-MAX_WBITS)
                        data = deflater.compress(data) + deflater.flush()
                        data = COMPRESSION_PREFIX + data
                    del item["compressed"]

                item["data"] = b64encode(data).decode()
            del item["decrypted"]


def decrypt_user_data(items: Union[List[Dict[str, Any]], Dict[str, Any]], keystore: Keystore):
    """
    Decrypt the data of each item in :ref: items
    If an item has already been decrypted, it won't be decrypted a second time

    :param items: Item or list of items to decrypt
    :param keystore: Keystore retrieved with the get_keystore method
    """

    # 1 item
    if not isinstance(items, (list, tuple)):
        items = [items]

    for i, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"Expected type 'dict' for item #{i} of 'items', got type '{type(item)}'")

        if item.get("decrypted"):
            continue

        if "data" not in item:
            raise ValueError(f"Expected key 'data' in item #{i} of 'items'")
        if "meta" not in item:
            raise ValueError(f"Expected key 'meta' in item #{i} of 'items'")

        meta = item["meta"]
        if meta not in keystore:
            raise NovelAIError("<UNKNOWN>", -1, f"Meta of item #{i} ({meta}) missing from keystore")

        key = keystore[meta]

        data, nonce, is_compressed = decrypt_data(b64decode(item["data"]), key)
        if data is not None:
            try:
                data = json.loads(data)
                item["data"] = data
                item["nonce"] = nonce
                item["decrypted"] = True
                item["compressed"] = is_compressed
                continue

            except json.JSONDecodeError:
                pass

        item["decrypted"] = False


def encrypt_user_data(items: Union[List[Dict[str, Any]], Dict[str, Any]], keystore: Keystore):
    """
    Encrypt the data of each item in :ref: items
    If an item has already been encrypted, it won't be encrypted a second time
    Must have been decrypted by decrypt_user_data()

    :param items: Item or list of items to encrypt
    :param keystore: Keystore retrieved with the get_keystore method
    """

    # 1 item
    if not isinstance(items, (list, tuple)):
        items = [items]

    for i, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"Expected type 'dict' for item #{i} of 'items', got type '{type(item)}'")

        if "decrypted" in item:
            if item["decrypted"]:
                if "data" not in item:
                    raise ValueError(f"Expected key 'data' in item #{i} of 'items'")
                if "meta" not in item:
                    raise ValueError(f"Expected key 'meta' in item #{i} of 'items'")
                if "nonce" not in item:
                    raise ValueError(f"Expected key 'nonce' in item #{i} of 'items'")
                if "compressed" not in item:
                    raise ValueError(f"Expected key 'compressed' in item #{i} of 'items'")

                meta = item["meta"]
                if meta not in keystore:
                    raise NovelAIError("<UNKNOWN>", -1, f"Meta of item #{i} ({meta}) missing from keystore")

                key = keystore[meta]

                data = json.dumps(item["data"], separators=(",", ":"), ensure_ascii=False)
                data = b64encode(encrypt_data(data, key, item["nonce"], item["compressed"])).decode()

                item["data"] = data
                del item["nonce"]
                del item["compressed"]

            del item["decrypted"]


def link_content_to_story(
    stories: Dict[str, Union[str, int, Dict[str, Any]]],
    story_contents: Union[List[Dict[str, Any]], Dict[str, Any]],
):
    """
    Link the story content to each story in :ref: stories
    """

    if not isinstance(stories, (list, tuple)):
        stories = [stories]

    if not isinstance(story_contents, (list, tuple)):
        story_contents = [story_contents]

    story_contents = {content["id"]: content for content in story_contents}

    for story in stories:
        if story.get("decrypted"):
            remote_id = story["data"].get("remoteStoryId")

            if remote_id and remote_id in story_contents and story_contents[remote_id].get("decrypted"):
                story["content"] = story_contents[remote_id]


def unlink_content_from_story(stories: Dict[str, Union[str, int, Dict[str, Any]]]):
    """
    Remove the story content from each story in :ref: stories
    """

    if not isinstance(stories, (list, tuple)):
        stories = [stories]

    for story in stories:
        if story.get("decrypted") and "content" in story:
            story.pop("content")


def get_decrypted_user_data(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter out items that have not been decrypted
    """

    return [item for item in items if item.get("decrypted", False)]


def tokens_to_b64(tokens: Iterable[int]) -> str:
    """
    Encode a list of tokens into a base64 string that can be sent to the API
    """

    return b64encode(b"".join(t.to_bytes(2, "little") for t in tokens)).decode()


def b64_to_tokens(b64: str) -> List[int]:
    """
    Decode a base64 string returned by the API into a list of tokens
    """

    b = b64decode(b64)

    return [int.from_bytes(b[i : i + 2], "little") for i in range(0, len(b), 2)]


def extract_preset_data(presets: List[Dict[str, Any]]) -> Dict[str, Preset]:
    """
    Transform a list of preset data into a dict of Preset objects indexed by their id
    """

    preset_list = {}
    for preset_data in presets:
        decompress_user_data(preset_data)
        preset_list[preset_data["id"]] = Preset.from_preset_data(preset_data["data"])

    return preset_list


def tokenize_if_not(model: Model, o: Union[str, List[int]]) -> List[int]:
    """
    Tokenize the string if it is not already tokenized
    """

    if isinstance(o, list):
        return o

    if not isinstance(o, str):
        raise ValueError(f"Expected type 'str' for 'o', got type '{type(o)}'")

    return Tokenizer.encode(model, o)


async def gather_asyncgenerator(agen: Union[AsyncGenerator[Any, None], AsyncIterable[Any]]) -> List[Any]:
    """
    Gather all the items of an async generator into a list
    """

    return [item async for item in agen]


# TODO: story tree builder
