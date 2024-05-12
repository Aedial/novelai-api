"""
Test if the content decryption/decompression is consistent with encryption/compression for downloaded content
"""
import base64
import json
from asyncio import run
from pathlib import Path
from typing import Any, List

import pytest

from tests.api.boilerplate import API, api_handle, error_handler  # noqa: F401  # pylint: disable=W0611

files_msgpackr = ["newstory", "red-riding-hood"]
files = [(file) for file in files_msgpackr]


def compare_in_out(type_name: str, items_in: List[Any], items_out: List[Any]) -> bool:
    fail_flags = "".join(("O" if item_in == item_out else "X") for item_in, item_out in zip(items_in, items_out))
    if "X" in fail_flags:
        print(f"{fail_flags.count('X')}/{len(fail_flags)} integrity checks failed for {type_name}")
        print(fail_flags)
        print("")

        return False

    print(f"All {len(fail_flags)} integrity checks succeeded for {type_name}\n")
    return True


@error_handler
async def novelaiunpacker_integrity(handle, file: str):
    unpacker = handle.novelaiunpacker
    config_path = Path(__file__).parent / "sanity_text_sets/msgpackr"

    # load document data taken directly from a NovelAi sample record
    f = open(f"{config_path}/{file}.b64")
    b64_data = f.read()
    f.close()

    f = open(f"{config_path}/{file}.json")
    json_orig = f.read()
    f.close()
    obj_orig = json.loads(json_orig)
    js_orig = unpacker.stringify(obj_orig)

    # decode data to retrieve raw byte array
    raw_data = base64.b64decode(b64_data)
    # unpack data into dict object
    content_doc = unpacker.unpack(raw_data)
    js_out = unpacker.stringify(content_doc)  # set default to str to handle JSON encoding of DateTime
    assert compare_in_out("msgpackr", js_orig, js_out)


@pytest.mark.parametrize("file", files)
async def test_novelaiunpacker(api_handle, file: str):  # noqa: F811  # pylint: disable=W0621
    await novelaiunpacker_integrity(api_handle, file)


if __name__ == "__main__":

    async def main():
        async with API() as api:
            await test_novelaiunpacker(api)

    run(main())