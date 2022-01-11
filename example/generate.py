from sys import version_info, path
from os.path import join, abspath, dirname

path.insert(0, abspath(join(dirname(__file__), "..")))

from novelai_api import NovelAI_API
from novelai_api.utils import (
    get_encryption_key,
    decrypt_user_data,
    map_meta_to_stories,
    assign_content_to_story,
)
from aiohttp import ClientSession

from logging import Logger
from asyncio import run

import json

# pip3 install pyyaml
import yaml

import base64

filename = join("credentials", "creds_example.txt")
with open(filename) as f:
    username, password = f.read().split(",")

logger = Logger("NovelAI")


async def main():
    async with ClientSession() as session:
        api = NovelAI_API(session, logger=logger)

        # a .. sLTgAMYAQAA= .. 64
        bin = base64.b85decode ('sLTgAMYAQAA=')
        print (bin)

        with open('delme', "wb") as f:
            f.write(bin)

        # b .. sLTgAMYAQQA= .. 65
        bin = base64.b85decode ('sLTgAMYAQQA=')
        print (bin)
        # c .. sLTgAMYAQgA= .. 66
        bin = base64.b85decode ('sLTgAMYAQgA=')
        print (bin)
        return ()

        print("login..")
        login = await api.high_level.login(username, password)

        print("get_encryption_key..")
        key = get_encryption_key(username, password)
        keystore = await api.high_level.get_keystore(key)

        print("generate..")
        input = "sLTgAMYAAgARDt4CIgHeAsYA"
        model = "genji-python-6b"
        params = {
            "generate_until_sentence": True,
            "max_length": 40,
            "min_length": 1,
            "prefix": "vanilla",
            "num_logprobs": 5,
            "repetition_pentalty": 1.13125,
            "repetition_penalty_range": 2048,
            "repetition_penalty_slope": 0.18,
            "return_full_text": False,
            "tail_free_sampling": 1,
            "temperature": 0.72,
            "top_k": 0,
            "top_p": 0.725,
            "use_cache": False,
            "use_string": False,
        }
        got = await api.low_level.generate(input, model, params)

        # tbd: https://beta.openai.com/tokenizer
        # If you need a programmatic interface for tokenizing text, check out the transformers package for python or the gpt-3-encoder package for node.js.
        # https://huggingface.co/transformers/model_doc/gpt2.html#gpt2tokenizerfast
        # https://github.com/NovelAI/transformers ?
        # https://github.com/wbrown/novelai-research-tool/tree/main/gpt-bpe ?
        # https://github.com/kingoflolz/mesh-transformer-jax/blob/master/device_sample.py#L88
        # https://github.com/latitudegames/GPT-3-Encoder
        # https://github.com/huggingface/transformers/blob/master/src/transformers/models/gpt2/tokenization_gpt2.py
        print(yaml.dump(got))

        print (got.get ('output'))
        bin = base64.b85decode (got.get ('output'))
        print (bin)

run(main())
