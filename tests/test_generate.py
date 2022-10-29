from sys import path
from os import environ as env
from os.path import join, abspath, dirname

path.insert(0, abspath(join(dirname(__file__), '..')))

from novelai_api import NovelAIAPI, NovelAIError
from novelai_api.Preset import Preset, Model
from novelai_api.GlobalSettings import GlobalSettings
from novelai_api.BanList import BanList
from novelai_api.BiasGroup import BiasGroup
from novelai_api.Tokenizer import Tokenizer
from novelai_api.utils import b64_to_tokens

from aiohttp import ClientSession, ClientConnectionError, ClientPayloadError
from logging import Logger, StreamHandler
from typing import Tuple

import pytest
import asyncio


# Text generation length
GENERATION_LENGTH = 10

WORKERS = int(env["PYTEST_XDIST_WORKER_COUNT"]) if "PYTEST_XDIST_WORKER_COUNT" in env else 1
# Minimum time for a test (in seconds)
MIN_TEST_TIME = 2 * WORKERS


async def run_test(func, *args, is_async: bool, attempts: int = 3):
    async def test_func():
        if is_async:
            try:
                async with ClientSession() as test_session:
                    api = NovelAIAPI(test_session)
                    return await func(api, *args)
            except Exception as test_exc:
                await test_session.close()
                raise test_exc

        else:
            api = NovelAIAPI()
            return await func(api, *args)

    e: Exception = RuntimeError("Unknown error")
    for _ in range(attempts):
        try:
            # inject api and execute the test
            return await asyncio.gather(test_func(), asyncio.sleep(MIN_TEST_TIME))

        except (asyncio.TimeoutError, ClientPayloadError):
            retry = True

        except NovelAIError as e:
            retry = any([
                e.status == 520,  # Cloudflare Unknown Error
                e.status == 524,  # Cloudflare Gateway Error
            ])

        if not retry:
            break

        await asyncio.sleep(10)

        # ping every 5 mins until connection is re-established
        async with ClientSession() as session:
            while True:
                try:
                    rsp = await session.get("https://www.google.com", timeout = 5 * 60)
                    rsp.raise_for_status()

                    break
                except (ClientConnectionError, asyncio.TimeoutError):
                    pass

    raise e


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
prompts = [input_txt]
tokenize_prompt = [False, True]

models = [*Model]
# NOTE: uncomment that if you're not Opus
# models.remove(Model.Genji)
# models.remove(Model.Snek)

models_presets = [(model, preset) for model in models for preset in Preset[model]]

model_input_permutation = [*permutations(models, prompts, tokenize_prompt)]
model_preset_input_permutation = [*permutations(models_presets, prompts, tokenize_prompt)]


async def simple_generate(api: NovelAIAPI, model: Model, preset: Preset, prompt: str, tokenize: bool):
    await api.high_level.login(username, password)

    logger.info(f"Using model {model.value}, preset {preset.name}\n")

    if tokenize:
        prompt = Tokenizer.encode(model, prompt)

    global_settings = GlobalSettings()
    gen = await api.high_level.generate(prompt, model, preset, global_settings)
    logger.info(gen)
    logger.info(Tokenizer.decode(model, b64_to_tokens(gen["output"])))


@pytest.mark.parametrize("model_preset,prompt,tokenize", model_preset_input_permutation)
async def test_simple_generate_sync(model_preset: Tuple[Model, Preset], prompt: str, tokenize: bool):
    # sync handler
    await run_test(simple_generate, *model_preset, prompt, tokenize, is_async = False)


@pytest.mark.parametrize("model_preset,prompt,tokenize", model_preset_input_permutation)
async def test_simple_generate_async(model_preset: Tuple[Model, Preset], prompt: str, tokenize: bool):
    # async handler
    await run_test(simple_generate, *model_preset, prompt, tokenize, is_async = True)


async def default_generate(api: NovelAIAPI, model: Model, prompt: str, tokenize: bool):
    await api.high_level.login(username, password)

    preset = Preset.from_default(model)
    preset["max_length"] = GENERATION_LENGTH

    logger.info(f"Using model {model.value}, preset {preset.name}\n")

    if tokenize:
        prompt = Tokenizer.encode(model, prompt)

    global_settings = GlobalSettings()
    gen = await api.high_level.generate(prompt, model, preset, global_settings)
    logger.info(gen)
    logger.info(Tokenizer.decode(model, b64_to_tokens(gen["output"])))


@pytest.mark.parametrize("model,prompt,tokenize", model_input_permutation)
async def test_default_generate_sync(model: Model, prompt: str, tokenize: bool):
    # sync handler
    await run_test(default_generate, model, prompt, tokenize, is_async = False)


@pytest.mark.parametrize("model,prompt,tokenize", model_input_permutation)
async def test_default_generate_async(model: Model, prompt: str, tokenize: bool):
    # async handler
    await run_test(default_generate, model, prompt, tokenize, is_async = True)


async def official_generate(api: NovelAIAPI, model: Model, prompt: str, tokenize: bool):
    await api.high_level.login(username, password)

    preset = Preset.from_official(model)
    preset["max_length"] = GENERATION_LENGTH

    logger.info(f"Using model {model.value}, preset {preset.name}\n")

    if tokenize:
        prompt = Tokenizer.encode(model, prompt)

    global_settings = GlobalSettings()
    gen = await api.high_level.generate(prompt, model, preset, global_settings)
    logger.info(gen)
    logger.info(Tokenizer.decode(model, b64_to_tokens(gen["output"])))


@pytest.mark.parametrize("model,prompt,tokenize", model_input_permutation)
async def test_official_generate_sync(model: Model, prompt: str, tokenize: bool):
    # sync handler
    await run_test(official_generate, model, prompt, tokenize, is_async = False)


@pytest.mark.parametrize("model,prompt,tokenize", model_input_permutation)
async def test_official_generate_async(model: Model, prompt: str, tokenize: bool):
    # async handler
    await run_test(official_generate, model, prompt, tokenize, is_async = True)


async def globalsettings_generate(api: NovelAIAPI, model: Model, preset: Preset, prompt: str, tokenize: bool):
    await api.high_level.login(username, password)
    preset["max_length"] = GENERATION_LENGTH

    logger.info(f"Using model {model.value}, preset {preset.name}\n")

    if tokenize:
        prompt = Tokenizer.encode(model, prompt)

    global_settings = GlobalSettings(bias_dinkus_asterism = True, ban_brackets = True,
                                     num_logprobs = GlobalSettings.NO_LOGPROBS)

    gen = await api.high_level.generate(prompt, model, preset, global_settings)
    logger.info(gen)
    logger.info(Tokenizer.decode(model, b64_to_tokens(gen["output"])))


@pytest.mark.parametrize("model_preset,prompt,tokenize", model_preset_input_permutation)
async def test_globalsettings_generate_sync(model_preset: Tuple[Model, Preset], prompt: str, tokenize: bool):
    # sync handler
    await run_test(globalsettings_generate, *model_preset, prompt, tokenize, is_async = False)


@pytest.mark.parametrize("model_preset,prompt,tokenize", model_preset_input_permutation)
async def test_globalsettings_generate_async(model_preset: Tuple[Model, Preset], prompt: str, tokenize: bool):
    # async handler
    await run_test(globalsettings_generate, *model_preset, prompt, tokenize, is_async = True)


async def bias_generate(api: NovelAIAPI, model: Model, preset: Preset, prompt: str, tokenize: bool):
    await api.high_level.login(username, password)
    preset["max_length"] = GENERATION_LENGTH

    logger.info(f"Using model {model.value}, preset {preset.name}\n")

    if tokenize:
        prompt = Tokenizer.encode(model, prompt)

    global_settings = GlobalSettings()
    global_settings["bias_dinkus_asterism"] = True
    global_settings["ban_brackets"] = True
    global_settings["num_logprobs"] = 1

    bias1 = BiasGroup(-0.1).add("It is", " It is", "It was", " It was",
                                Tokenizer.encode(model, "There is")) \
                           .add(Tokenizer.encode(model, "There are"))
    bias1 += " as it is"

    bias2 = BiasGroup(0.1).add(" because", " since").add(" why").add(" when", " about")
    bias2 += "as it is"

    gen = await api.high_level.generate(prompt, model, preset, global_settings,
                                        biases = (bias1, bias2))
    logger.info(gen)
    logger.info(Tokenizer.decode(model, b64_to_tokens(gen["output"])))


@pytest.mark.parametrize("model_preset,prompt,tokenize", model_preset_input_permutation)
async def test_bias_generate_sync(model_preset: Tuple[Model, Preset], prompt: str, tokenize: bool):
    # sync handler
    await run_test(bias_generate, *model_preset, prompt, tokenize, is_async = False)


@pytest.mark.parametrize("model_preset,prompt,tokenize", model_preset_input_permutation)
async def test_bias_generate_async(model_preset: Tuple[Model, Preset], prompt: str, tokenize: bool):
    # async handler
    await run_test(bias_generate, *model_preset, prompt, tokenize, is_async = True)


async def ban_generate(api: NovelAIAPI, model: Model, preset: Preset, prompt: str, tokenize: bool):
    await api.high_level.login(username, password)
    preset["max_length"] = GENERATION_LENGTH

    logger.info(f"Using model {model.value}, preset {preset.name}\n")

    if tokenize:
        prompt = Tokenizer.encode(model, prompt)

    global_settings = GlobalSettings()
    global_settings["bias_dinkus_asterism"] = True
    global_settings["ban_brackets"] = True
    global_settings["num_logprobs"] = 1

    banned = BanList().add("***", "---", Tokenizer.encode(model, "///")).add("fairly")
    banned += "commonly"
    banned += " commonly"

    gen = await api.high_level.generate(prompt, model, preset, global_settings,
                                        bad_words = banned)
    logger.info(gen)
    logger.info(Tokenizer.decode(model, b64_to_tokens(gen["output"])))


@pytest.mark.parametrize("model_preset,prompt,tokenize", model_preset_input_permutation)
async def test_ban_generate_sync(model_preset: Tuple[Model, Preset], prompt: str, tokenize: bool):
    # sync handler
    await run_test(ban_generate, *model_preset, prompt, tokenize, is_async = False)


@pytest.mark.parametrize("model_preset,prompt,tokenize", model_preset_input_permutation)
async def test_ban_generate_async(model_preset: Tuple[Model, Preset], prompt: str, tokenize: bool):
    # async handler
    await run_test(ban_generate, *model_preset, prompt, tokenize, is_async = True)


async def ban_and_bias_generate(api: NovelAIAPI, model: Model, preset: Preset, prompt: str, tokenize: bool):
    await api.high_level.login(username, password)
    preset["max_length"] = GENERATION_LENGTH

    logger.info(f"Using model {model.value}, preset {preset.name}\n")

    if tokenize:
        prompt = Tokenizer.encode(model, prompt)

    global_settings = GlobalSettings()
    global_settings["bias_dinkus_asterism"] = True
    global_settings["ban_brackets"] = True
    global_settings["num_logprobs"] = 1

    banned = BanList().add("***", "---", Tokenizer.encode(model, "///")).add("fairly")
    banned += "commonly"
    banned += " commonly"

    bias2 = BiasGroup(0.1).add(" because", " since").add(" why").add(" when", " about")
    bias2 += "as it is"

    gen = await api.high_level.generate(prompt, model, preset, global_settings,
                                        bad_words = banned, biases = [bias2])
    logger.info(gen)
    logger.info(Tokenizer.decode(model, b64_to_tokens(gen["output"])))


@pytest.mark.parametrize("model_preset,prompt,tokenize", model_preset_input_permutation)
async def test_ban_and_bias_generate_sync(model_preset: Tuple[Model, Preset], prompt: str, tokenize: bool):
    # sync handler
    await run_test(ban_and_bias_generate, *model_preset, prompt, tokenize, is_async = False)


@pytest.mark.parametrize("model_preset,prompt,tokenize", model_preset_input_permutation)
async def test_ban_and_bias_generate_async(model_preset: Tuple[Model, Preset], prompt: str, tokenize: bool):
    # async handler
    await run_test(ban_and_bias_generate, *model_preset, prompt, tokenize, is_async = True)


async def ban_and_bias_generate_streaming(api: NovelAIAPI, model: Model, preset: Preset, prompt: str, tokenize: bool):
    await api.high_level.login(username, password)
    preset["max_length"] = GENERATION_LENGTH

    logger.info(f"Using model {model.value}, preset {preset.name}\n")

    if tokenize:
        prompt = Tokenizer.encode(model, prompt)

    global_settings = GlobalSettings()
    global_settings["bias_dinkus_asterism"] = True
    global_settings["ban_brackets"] = True
    global_settings["num_logprobs"] = 1

    banned = BanList().add("***", "---", Tokenizer.encode(model, "///")).add("fairly")
    banned += "commonly"
    banned += " commonly"

    bias2 = BiasGroup(0.1).add(" because", " since").add(" why").add(" when", " about")
    bias2 += "as it is"

    async for i in api.high_level.generate_stream(prompt, model, preset, global_settings,
                                                  bad_words = banned, biases = [bias2]):
        logger.info(i)
        logger.info(Tokenizer.decode(model, b64_to_tokens(i["token"])))


@pytest.mark.parametrize("model_preset,prompt,tokenize", model_preset_input_permutation)
async def test_ban_and_bias_generate_streaming_sync(model_preset: Tuple[Model, Preset], prompt: str, tokenize: bool):
    # sync handler
    await run_test(ban_and_bias_generate_streaming, *model_preset, prompt, tokenize, is_async = False)


@pytest.mark.parametrize("model_preset,prompt,tokenize", model_preset_input_permutation)
async def test_ban_and_bias_generate_streaming_async(model_preset: Tuple[Model, Preset], prompt: str, tokenize: bool):
    # async handler
    await run_test(ban_and_bias_generate_streaming, *model_preset, prompt, tokenize, is_async = True)
