from typing import Tuple

import pytest

from novelai_api import NovelAIAPI
from novelai_api.GlobalSettings import GlobalSettings
from novelai_api.Preset import Model, Preset
from novelai_api.Tokenizer import Tokenizer
from novelai_api.utils import b64_to_tokens
from tests.api.boilerplate import api_handle  # noqa: F401  # pylint: disable=W0611

prompt = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Aliquam at dolor dictum, interdum est sed, consequat arcu. Pellentesque in massa eget lorem fermentum placerat in pellentesque purus. Suspendisse potenti. Integer interdum, felis quis porttitor volutpat, est mi rutrum massa, venenatis viverra neque lectus semper metus. Pellentesque in neque arcu. Ut at arcu blandit purus aliquet finibus. Suspendisse laoreet risus a gravida semper. Aenean scelerisque et sem vitae feugiat. Quisque et interdum diam, eu vehicula felis. Ut tempus quam eros, et sollicitudin ligula auctor at. Integer at tempus dui, quis pharetra purus. Duis venenatis tincidunt tellus nec efficitur. Nam at malesuada ligula."  # noqa: E501  # pylint: disable=C0301
models = [*Model]
# NOTE: uncomment that if you're not Opus
# models.remove(Model.Genji)
# models.remove(Model.Snek)

models_presets = [(model, preset) for model in models for preset in Preset[model]]
models_presets_default = [(model, Preset.from_default(model)) for model in models]


async def simple_generate(api: NovelAIAPI, model: Model, preset: Preset):
    logger = api.logger
    logger.info("Using model %s, preset %s\n", model.value, preset.name)

    global_settings = GlobalSettings()
    gen = await api.high_level.generate(prompt, model, preset, global_settings)
    logger.info(gen)
    logger.info(Tokenizer.decode(model, b64_to_tokens(gen["output"])))


@pytest.mark.parametrize("model_preset", models_presets)
async def test_presets(api_handle, model_preset: Tuple[Model, Preset]):  # noqa: F811  # pylint: disable=W0621
    await api_handle.api.run_test(simple_generate, *model_preset)


@pytest.mark.parametrize("model_preset", models_presets_default)
async def test_presets_default(api_handle, model_preset: Tuple[Model, Preset]):  # noqa: F811  # pylint: disable=W0621
    await api_handle.api.run_test(simple_generate, *model_preset)
