from boilerplate import API
from novelai_api.Preset import Model, Preset
from novelai_api.GlobalSettings import GlobalSettings
from novelai_api.BanList import BanList
from novelai_api.BiasGroup import BiasGroup
from novelai_api.Tokenizer import Tokenizer
from novelai_api.utils import b64_to_tokens

from asyncio import run

from typing import Optional, List


async def main():
    async with API() as api_handler:
        api = api_handler.api
        logger = api_handler.logger

        model = Model.Sigurd
#        model = Model.Euterpe
#        model = Model.Krake

        # plain text prompt
        prompt = "***"
        # prompt encoded in tokens
#        prompt = Tokenizer.encode(model, "***")

        # instantiation from default (presets/presets_6B_v4/default.txt)
        preset = Preset.from_default(model)
        # instantiation from official file (presets/presets_6B_v4)
#        preset = Preset.from_official(model, "Storywriter")
        # instantiation from file
#        preset = Preset.from_file("novelai_api/presets/presets_6B_v4/Storywriter.txt")
        # instantiation of a new reset
#        preset = Preset("new preset", model)
        # modification of the preset (this does not modify other copies of official presets)
        preset["max_length"] = 20

        # instantiate with arguments
        global_settings = GlobalSettings(num_logprobs = GlobalSettings.NO_LOGPROBS)
        # change arguments after instantiation
        global_settings["bias_dinkus_asterism"] = True

        # no ban list
        bad_words: Optional[BanList] = None
        # empty ban list
#        bad_words = BanList()
        # ban list with elements in it
#        bad_words = BanList(" cat", " dog", " boy")
        # disabled ban list with elements in it
#        bad_words = BanList(" cat", " dog", " boy", enabled = False)
        if bad_words is not None:
            bad_words.add(" man", " Man", " father")
            bad_words += " Father"

        bias_groups: List[BiasGroup] = []
        bias_group1 = BiasGroup(0.15)
        bias_group2 = BiasGroup(0.05)
#        bias_groups.extend([bias_group1, bias_group2])

        if bias_groups:
            bias_group1.add("very", " very", " slightly", " incredibly", " enormously", " loudly")
            bias_group1 += " proverbially"
            bias_group2 += " interestingly"
            bias_group2 += " brutally"

        # no module
        module = None
        # CrossGenre module (module names can be found in the network tab)
#        module = "general_crossgenre"
        # Custom module (OccultSage's Mass Effect v2)
#        module = "6B-v4:c6021aaa523e2dcb8588848b5fd4e2516dd4bb7107268aaa6050b5430c3a4b47:"
#                       "b764a71f139d0d829ed0f3077f026db43fdb25bc6b45ac508e85dd4c405a2fae"

        # normal generation
        gen = await api.high_level.generate(prompt, model, preset, global_settings, bad_words, bias_groups, module)
        logger.info(gen["output"])
        logger.info(b64_to_tokens(gen["output"]))
        logger.info(Tokenizer.decode(model, b64_to_tokens(gen["output"])))

        # streamed generation
        async for token in api.high_level.generate_stream(prompt, model, preset, global_settings,
                                                          bad_words, bias_groups, module):
            logger.info("%s  %s  '%s'",
                        token["token"],
                        b64_to_tokens(token["token"]),
                        Tokenizer.decode(model, b64_to_tokens(token["token"])))

        # ... and more examples can be found in tests/test_generate.py

run(main())
