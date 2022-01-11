from sys import version_info, path
from os.path import join, abspath, dirname

path.insert(0, abspath(join(dirname(__file__), "..")))

from novelai_api import NovelAI_API
from aiohttp import ClientSession

from logging import Logger
import asyncio

import json

import base64
import struct

filename = join("credentials", "creds_example.txt")
with open(filename) as f:
    username, password = f.read().split(",")

logger = Logger("NovelAI")


async def main():
    async with ClientSession() as session:
        api = NovelAI_API(session, logger=logger)

        input_string = "hello world"

        # NB: Generation of the tokenized input from “token_ids” is currently unused
        # because of the “params["use_string"] = True” clause in “def generate”.

        # Use https://beta.openai.com/tokenizer to generate the input token IDs.
        token_ids = [31373, 995]  # “hello world”

        novelai_prefix = bytes([0xB0, 0xB4, 0xE0, 0x00, 0xC6, 0x00])

        bytes_input = novelai_prefix
        for token in token_ids:
            bytes_input += struct.pack("<H", token)
        print("input:")
        print(bytes_input)
        input = base64.urlsafe_b64encode(bytes_input).decode("utf-8")
        print("b64i: " + input)

        print("login..")
        login = await api.high_level.login(username, password)

        print("generate..")
        model = "genji-python-6b"
        params = {
            "temperature": 0.72,
            "max_length": 40,
            "min_length": 1,
            "top_k": 0,
            "top_p": 0.725,
            "tail_free_sampling": 1,
            "repetition_penalty": 1.13125,
            "repetition_penalty_range": 2048,
            "repetition_penalty_slope": 0.18,
            "repetition_penalty_frequency": 0,
            "repetition_penalty_presence": 0,
            "generate_until_sentence": True,
            "use_cache": False,
            "use_string": False,
            "return_full_text": True,
            "prefix": "vanilla",
            "order": [0, 1, 2, 3],
        }

        got = await api.low_level.generate(input_string, model, params)

        print(got.get("output"))

        # Might be useful with “params["use_string"] = False”?
        #
        # output = base64.urlsafe_b64decode(got.get("output"))
        # for ix in range(6, len(output), 2):
        #    print(struct.unpack("<H", output[ix : ix + 2]))


asyncio.run(main())
