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
from asyncio import run
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

        for model in Model:
            preset = Preset.from_default(model)
            global_settings = GlobalSettings(ban_brackets = True, bias_dinkus_asterism = True)
            logger.info(f"Using model {model.value}\n")

            input_txt = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Aliquam at dolor dictum, interdum est sed, consequat arcu. Pellentesque in massa eget lorem fermentum placerat in pellentesque purus. Suspendisse potenti. Integer interdum, felis quis porttitor volutpat, est mi rutrum massa, venenatis viverra neque lectus semper metus. Pellentesque in neque arcu. Ut at arcu blandit purus aliquet finibus. Suspendisse laoreet risus a gravida semper. Aenean scelerisque et sem vitae feugiat. Quisque et interdum diam, eu vehicula felis. Ut tempus quam eros, et sollicitudin ligula auctor at. Integer at tempus dui, quis pharetra purus. Duis venenatis tincidunt tellus nec efficitur. Nam at malesuada ligula."
            input = Tokenizer.encode(input_txt)

            preset["max_length"] = 100
            logger.info("gen1:")
            gen1 = await api.high_level.generate(input, model, preset, global_settings)
            logger.info(gen1)
            logger.info(Tokenizer.decode(b64_to_tokens(gen1["output"])))
            logger.info("")
            preset["max_length"] = 20

            global_settings.bias_dinkus_asterism = True
            global_settings.ban_brackets = True

            global_settings.num_logprobs = GlobalSettings.NO_LOGPROBS
            preset = Preset.from_official(model)

            logger.info("gen2:")
            gen2 = await api.high_level.generate(input_txt, model, preset, global_settings)
            logger.info(gen2)
            logger.info(Tokenizer.decode(b64_to_tokens(gen2["output"])))
            logger.info("")

            bias1 = BiasGroup(-0.1).add("It is", " It is", "It was", " It was",
                                        Tokenizer.encode("There is")) \
                                .add(Tokenizer.encode("There are"))
            bias1 += " as it is"

            bias2 = BiasGroup(0.1).add(" because", " since").add(" why").add(" when", " about")
            bias2 += "as it is"

            global_settings.num_logprobs = 1
            preset = Preset.from_official(model)

            logger.info("gen3:")
            gen3 = await api.high_level.generate(input, model, preset, global_settings,
                                                 biases = [bias1, bias2])
            logger.info(gen3)
            logger.info(Tokenizer.decode(b64_to_tokens(gen3["output"])))
            logger.info("")

            banned = BanList().add("***", "---", Tokenizer.encode("///")).add("fairly")
            banned += "commonly"
            banned += " commonly"

            logger.info("gen4:")
            gen4 = await api.high_level.generate(input_txt, model, preset, global_settings,
                                                 bad_words = banned)
            logger.info(gen4)
            logger.info(Tokenizer.decode(b64_to_tokens(gen4["output"])))
            logger.info("")

            logger.info("gen5:")
            gen5 = await api.high_level.generate(input_txt, model, preset, global_settings,
                                                 bad_words = banned, biases = [bias2])
            logger.info(gen5)
            logger.info(Tokenizer.decode(b64_to_tokens(gen5["output"])))
            logger.info("\n")

run(main())