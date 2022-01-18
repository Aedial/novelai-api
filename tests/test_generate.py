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
from typing import Union, List, Tuple

import pytest

def permutations(*args):
    args = [list(a) for a in args if len(a)]
    l = len(args)
    ilist = [0] * l

    while True:
        yield [arg[i] for arg, i in zip(args, ilist)]

        ilist[0] += 1
        for i in range(l):
            if ilist[i] == len(args[i]):
                if i + 1 == l:  # end, don't overflow
                    return
                else:
                    ilist[i + 1] += 1
                    ilist[i] = 0
            else:
                break

if "NAI_USERNAME" not in env or "NAI_PASSWORD" not in env:
    raise RuntimeError("Please ensure that NAI_USERNAME and NAI_PASSWORD are set in your environment")

username = env["NAI_USERNAME"]
password = env["NAI_PASSWORD"]

logger = Logger("NovelAI")
logger.addHandler(StreamHandler())

input_txt = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Aliquam at dolor dictum, interdum est sed, consequat arcu. Pellentesque in massa eget lorem fermentum placerat in pellentesque purus. Suspendisse potenti. Integer interdum, felis quis porttitor volutpat, est mi rutrum massa, venenatis viverra neque lectus semper metus. Pellentesque in neque arcu. Ut at arcu blandit purus aliquet finibus. Suspendisse laoreet risus a gravida semper. Aenean scelerisque et sem vitae feugiat. Quisque et interdum diam, eu vehicula felis. Ut tempus quam eros, et sollicitudin ligula auctor at. Integer at tempus dui, quis pharetra purus. Duis venenatis tincidunt tellus nec efficitur. Nam at malesuada ligula."
input_tokens = Tokenizer.encode(input_txt)
input = (input_txt, input_tokens)

models = [*Model]
# NOTE: uncomment that if you're not Opus
# models.remove(Model.Euterpe)
# models.remove(Model.Snek)

models_presets = [(model, preset) for model in models for preset in Preset[model]]

model_input_permutation = [*permutations(models, input)]
model_preset_input_permutation = [*permutations(models_presets, input)]

async def simple_generate(api: NovelAI_API, model: Model, preset: Preset, input: Union[str, List[int]]):
    await api.high_level.login(username, password)

    logger.info(f"Using model {model.value}, preset {preset.name}\n")

    global_settings = GlobalSettings()
    gen = await api.high_level.generate(input, model, preset, global_settings)
    logger.info(Tokenizer.decode(b64_to_tokens(gen["output"])))

@pytest.mark.parametrize("model_preset,input", model_preset_input_permutation)
async def test_simple_generate_sync(model_preset: Tuple[Model, Preset], input: Union[str, List[int]]):
    # sync handler
    api = NovelAI_API()
    await simple_generate(api, *model_preset, input)

@pytest.mark.parametrize("model_preset,input", model_preset_input_permutation)
async def test_simple_generate_async(model_preset: Tuple[Model, Preset], input: Union[str, List[int]]):
    # async handler
    async with ClientSession() as session:
        api = NovelAI_API(session)
        await simple_generate(api, *model_preset, input)


async def default_generate(api: NovelAI_API, model: Model, input: Union[str, List[int]]):
    await api.high_level.login(username, password)

    preset = Preset.from_default(model)

    logger.info(f"Using model {model.value}, preset {preset.name}\n")

    global_settings = GlobalSettings()
    gen = await api.high_level.generate(input, model, preset, global_settings)
    logger.info(Tokenizer.decode(b64_to_tokens(gen["output"])))

@pytest.mark.parametrize("model,input", model_input_permutation)
async def test_default_generate_sync(model: Model, input: Union[str, List[int]]):
    # sync handler
    api = NovelAI_API()
    await default_generate(api, model, input)

@pytest.mark.parametrize("model,input", model_input_permutation)
async def test_default_generate_async(model: Model, input: Union[str, List[int]]):
    # async handler
    async with ClientSession() as session:
        api = NovelAI_API(session)
        await default_generate(api, model, input)


async def official_generate(api: NovelAI_API, model: Model, input: Union[str, List[int]]):
    await api.high_level.login(username, password)

    preset = Preset.from_official(model)

    logger.info(f"Using model {model.value}, preset {preset.name}\n")

    global_settings = GlobalSettings()
    gen = await api.high_level.generate(input, model, preset, global_settings)
    logger.info(Tokenizer.decode(b64_to_tokens(gen["output"])))

@pytest.mark.parametrize("model,input", model_input_permutation)
async def test_official_generate_sync(model: Model, input: Union[str, List[int]]):
    # sync handler
    api = NovelAI_API()
    await official_generate(api, model, input)

@pytest.mark.parametrize("model,input", model_input_permutation)
async def test_official_generate_async(model: Model, input: Union[str, List[int]]):
    # async handler
    async with ClientSession() as session:
        api = NovelAI_API(session)
        await official_generate(api, model, input)


async def globalsettings_generate(api: NovelAI_API, model: Model, preset: Preset, input: Union[str, List[int]]):
    await api.high_level.login(username, password)

    logger.info(f"Using model {model.value}, preset {preset.name}\n")

    global_settings = GlobalSettings()
    global_settings.bias_dinkus_asterism = True
    global_settings.ban_brackets = True
    global_settings.num_logprobs = GlobalSettings.NO_LOGPROBS

    gen = await api.high_level.generate(input, model, preset, global_settings)
    logger.info(Tokenizer.decode(b64_to_tokens(gen["output"])))

@pytest.mark.parametrize("model_preset,input", model_preset_input_permutation)
async def test_globalsettings_generate_sync(model_preset: Tuple[Model, Preset], input: Union[str, List[int]]):
    # sync handler
    api = NovelAI_API()
    await globalsettings_generate(api, *model_preset, input)

@pytest.mark.parametrize("model_preset,input", model_preset_input_permutation)
async def test_globalsettings_generate_async(model_preset: Tuple[Model, Preset], input: Union[str, List[int]]):
    # async handler
    async with ClientSession() as session:
        api = NovelAI_API(session)
        await globalsettings_generate(api, *model_preset, input)


async def bias_generate(api: NovelAI_API, model: Model, preset: Preset, input: Union[str, List[int]]):
    await api.high_level.login(username, password)

    logger.info(f"Using model {model.value}, preset {preset.name}\n")

    global_settings = GlobalSettings()
    global_settings.bias_dinkus_asterism = True
    global_settings.ban_brackets = True
    global_settings.num_logprobs = 1

    bias1 = BiasGroup(-0.1).add("It is", " It is", "It was", " It was",
                                Tokenizer.encode("There is")) \
                           .add(Tokenizer.encode("There are"))
    bias1 += " as it is"

    bias2 = BiasGroup(0.1).add(" because", " since").add(" why").add(" when", " about")
    bias2 += "as it is"

    gen = await api.high_level.generate(input, model, preset, global_settings,
                                        biases = (bias1, bias2))
    logger.info(Tokenizer.decode(b64_to_tokens(gen["output"])))

@pytest.mark.parametrize("model_preset,input", model_preset_input_permutation)
async def test_bias_generate_sync(model_preset: Tuple[Model, Preset], input: Union[str, List[int]]):
    # sync handler
    api = NovelAI_API()
    await bias_generate(api, *model_preset, input)

@pytest.mark.parametrize("model_preset,input", model_preset_input_permutation)
async def test_bias_generate_async(model_preset: Tuple[Model, Preset], input: Union[str, List[int]]):
    # async handler
    async with ClientSession() as session:
        api = NovelAI_API(session)
        await bias_generate(api, *model_preset, input)


async def ban_generate(api: NovelAI_API, model: Model, preset: Preset, input: Union[str, List[int]]):
    await api.high_level.login(username, password)

    logger.info(f"Using model {model.value}, preset {preset.name}\n")

    global_settings = GlobalSettings()
    global_settings.bias_dinkus_asterism = True
    global_settings.ban_brackets = True
    global_settings.num_logprobs = 1

    banned = BanList().add("***", "---", Tokenizer.encode("///")).add("fairly")
    banned += "commonly"
    banned += " commonly"

    gen = await api.high_level.generate(input, model, preset, global_settings,
                                        bad_words = banned)
    logger.info(Tokenizer.decode(b64_to_tokens(gen["output"])))

@pytest.mark.parametrize("model_preset,input", model_preset_input_permutation)
async def test_ban_generate_sync(model_preset: Tuple[Model, Preset], input: Union[str, List[int]]):
    # sync handler
    api = NovelAI_API()
    await ban_generate(api, *model_preset, input)

@pytest.mark.parametrize("model_preset,input", model_preset_input_permutation)
async def test_ban_generate_async(model_preset: Tuple[Model, Preset], input: Union[str, List[int]]):
    # async handler
    async with ClientSession() as session:
        api = NovelAI_API(session)
        await ban_generate(api, *model_preset, input)


async def ban_and_bias_generate(api: NovelAI_API, model: Model, preset: Preset, input: Union[str, List[int]]):
    await api.high_level.login(username, password)

    logger.info(f"Using model {model.value}, preset {preset.name}\n")

    global_settings = GlobalSettings()
    global_settings.bias_dinkus_asterism = True
    global_settings.ban_brackets = True
    global_settings.num_logprobs = 1

    banned = BanList().add("***", "---", Tokenizer.encode("///")).add("fairly")
    banned += "commonly"
    banned += " commonly"

    bias2 = BiasGroup(0.1).add(" because", " since").add(" why").add(" when", " about")
    bias2 += "as it is"

    gen = await api.high_level.generate(input, model, preset, global_settings,
                                        bad_words = banned, biases = [bias2])
    logger.info(Tokenizer.decode(b64_to_tokens(gen["output"])))

@pytest.mark.parametrize("model_preset,input", model_preset_input_permutation)
async def test_ban_and_bias_generate_sync(model_preset: Tuple[Model, Preset], input: Union[str, List[int]]):
    # sync handler
    api = NovelAI_API()
    await ban_and_bias_generate(api, *model_preset, input)

@pytest.mark.parametrize("model_preset,input", model_preset_input_permutation)
async def test_ban_and_bias_generate_async(model_preset: Tuple[Model, Preset], input: Union[str, List[int]]):
    # async handler
    async with ClientSession() as session:
        api = NovelAI_API(session)
        await ban_generate(api, *model_preset, input)