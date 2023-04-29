"""
Test if the generated content is consistent with the frontend
"""

import json
from pathlib import Path
from typing import Any, Dict, Tuple

import pytest

from novelai_api.GlobalSettings import GlobalSettings
from novelai_api.Preset import Model, Preset
from novelai_api.Tokenizer import Tokenizer
from novelai_api.utils import b64_to_tokens
from tests.api.boilerplate import api_handle, error_handler  # noqa: F401  # pylint: disable=W0611

models = [*Model]
# NOTE: uncomment that if you're not Opus
# models.remove(Model.Genji)
# models.remove(Model.Snek)

# TODO: add Genji and Snek in sanity_text_sets
models = list(set(models) - {Model.Genji, Model.Snek, Model.HypeBot, Model.Inline})

config_path = Path(__file__).parent / "sanity_text_sets"
model_configs = [(model, p) for model in models for p in (config_path / model.value).iterdir()]


@pytest.mark.parametrize("model_config", model_configs)
@error_handler
async def test_textgen_sanity(api_handle, model_config: Tuple[Model, Path]):  # noqa: F811  # pylint: disable=W0621
    api = api_handle.api
    logger = api.logger

    model, path = model_config
    config: Dict[str, Any] = json.loads(path.read_text("utf-8"))

    missing_keys = {"prompt", "preset", "global_settings"} - set(config.keys())
    if missing_keys:
        raise ValueError(f"Config {path} missing keys {', '.join(missing_keys)}")

    prompt = config["prompt"]
    preset_data = config["preset"]
    preset = (
        Preset.from_official(model, preset_data)
        if isinstance(preset_data, str)
        else Preset.from_preset_data(preset_data)
    )
    global_settings = GlobalSettings(**config["global_settings"])
    bans = None  # TODO
    biases = None  # TODO
    module = config.get("module", None)

    logger.info("Using model %s, preset %s (%s)\n", model.value, preset.name, path)

    gen = await api.high_level.generate(prompt, model, preset, global_settings, bans, biases, module)
    # logger.info(gen)

    result = config.get("result", None)
    if result is not None:
        assert Tokenizer.decode(model, b64_to_tokens(gen["output"])) == result

    logprobs = config.get("logprobs", None)
    if logprobs is not None:
        assert logprobs == gen["logprobs"]
