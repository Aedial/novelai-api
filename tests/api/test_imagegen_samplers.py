"""
Test which samplers currently work
"""

import asyncio
import itertools
from typing import Tuple

import pytest

from novelai_api import NovelAIError
from novelai_api.ImagePreset import ImageModel, ImagePreset, ImageSampler, UCPreset
from tests.api.boilerplate import API, api_handle, error_handler  # noqa: F401  # pylint: disable=W0611

sampler_xfail = pytest.mark.xfail(True, raises=NovelAIError, reason="The sampler doesn't currently work")

models = list(ImageModel)
models.remove(ImageModel.Inpainting_Anime_Full)
models.remove(ImageModel.Inpainting_Anime_Curated)
models.remove(ImageModel.Inpainting_Furry)
models.remove(ImageModel.Inpainting_Anime_v3)
models.remove(ImageModel.Inpainting_Furry_v3)

samplers = list(ImageSampler)
model_samplers = list(itertools.product(models, samplers))


@pytest.mark.parametrize(
    "model_sampler",
    [
        pytest.param(e, marks=sampler_xfail) if e[1] in (ImageSampler.nai_smea, ImageSampler.plms) else e
        for e in model_samplers
    ],
)
@error_handler
async def test_samplers(
    api_handle, model_sampler: Tuple[ImageModel, ImageSampler]  # noqa: F811  # pylint: disable=W0621
):
    api = api_handle.api
    model, sampler = model_sampler

    # ddim_v3 only work with Anime v3
    if sampler is ImageSampler.ddim_v3 and model not in (ImageModel.Anime_v3,):
        return

    logger = api_handle.logger
    logger.info(f"Testing model {model} with sampler {sampler}")

    preset = ImagePreset.from_default_config(model)
    preset["sampler"] = sampler
    preset.copy()

    # Furry doesn't have UCPreset.Preset_Low_Quality_Bad_Anatomy
    if model is ImageModel.Furry:
        preset.uc_preset = UCPreset.Preset_Low_Quality

    async for _, _ in api.high_level.generate_image("1girl", model, preset):
        pass


if __name__ == "__main__":

    async def main():
        async with API() as api:
            await test_samplers(api, (ImageModel.Anime_v3, ImageSampler.ddim_v3))

    asyncio.run(main())
