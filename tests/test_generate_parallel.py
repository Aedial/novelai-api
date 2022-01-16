# Test to ensure the wrapper works with parallelism, do not spam the API !

from sys import path
from os import environ as env
from os.path import join, abspath, dirname

path.insert(0, abspath(join(dirname(__file__), '..')))

from novelai_api import NovelAI_API
from novelai_api.Preset import Preset, Model
from novelai_api.GlobalSettings import GlobalSettings
from novelai_api.BanList import BanList
from novelai_api.BiasGroup import BiasGroup
from novelai_api.Tokenizer import Tokenizer
from novelai_api.utils import b64_to_tokens

from aiohttp import ClientSession
from logging import Logger, StreamHandler
from asyncio import run, gather
from json import dumps

if "NAI_USERNAME" not in env or "NAI_PASSWORD" not in env:
    raise RuntimeError("Please ensure that NAI_USERNAME and NAI_PASSWORD are set in your environment")

username = env["NAI_USERNAME"]
password = env["NAI_PASSWORD"]

logger = Logger("NovelAI")
logger.addHandler(StreamHandler())

async def main():
    async with ClientSession() as session:
        api = NovelAI_API(session, logger = logger)
        logger.info(await api.high_level.login(username, password))
        logger.info("")

        model = Model.Sigurd
        preset = Preset.from_default(model)
        global_settings = GlobalSettings(ban_brackets = True, bias_dinkus_asterism = True)

        logger.info(f"Using model {model.value}\n")

        input_txt = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Aliquam at dolor dictum, interdum est sed, consequat arcu. Pellentesque in massa eget lorem fermentum placerat in pellentesque purus. Suspendisse potenti. Integer interdum, felis quis porttitor volutpat, est mi rutrum massa, venenatis viverra neque lectus semper metus. Pellentesque in neque arcu. Ut at arcu blandit purus aliquet finibus. Suspendisse laoreet risus a gravida semper. Aenean scelerisque et sem vitae feugiat. Quisque et interdum diam, eu vehicula felis. Ut tempus quam eros, et sollicitudin ligula auctor at. Integer at tempus dui, quis pharetra purus. Duis venenatis tincidunt tellus nec efficitur. Nam at malesuada ligula."
        input = Tokenizer.encode(input_txt)

        preset["max_length"] = 100
        gens = [api.high_level.generate(input, model, preset, global_settings) for _ in range(10)]
        results = await gather(*gens)
        for i, gen in enumerate(results):
            logger.info(f"Gen {i}:")
            logger.info("\t" + Tokenizer.decode(b64_to_tokens(gen["output"])))
            logger.info("")

run(main())