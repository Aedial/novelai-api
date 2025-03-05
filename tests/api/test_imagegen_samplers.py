"""
Test which samplers currently work
"""

import asyncio
import itertools
from pathlib import Path
from typing import Tuple

import pytest

from novelai_api import NovelAIError
from novelai_api.ImagePreset import ImageModel, ImagePreset, ImageSampler
from tests.api.boilerplate import API, api_handle, error_handler  # noqa: F401  # pylint: disable=W0611

sampler_xfail = pytest.mark.xfail(strict=False, raises=NovelAIError, reason="The sampler might not work")

models = list(ImageModel)

# remove outdated models
models.remove(ImageModel.Anime_Full)
models.remove(ImageModel.Anime_Curated)
models.remove(ImageModel.Furry)
models.remove(ImageModel.Anime_v2)
models.remove(ImageModel.Anime_v3)
models.remove(ImageModel.Furry_v3)
models.remove(ImageModel.Anime_v4_preview)

# remove inpainting models
models.remove(ImageModel.Inpainting_Anime_Full)
models.remove(ImageModel.Inpainting_Anime_Curated)
models.remove(ImageModel.Inpainting_Furry)
models.remove(ImageModel.Inpainting_Anime_v3)
models.remove(ImageModel.Inpainting_Furry_v3)
models.remove(ImageModel.Inpainting_Anime_v4_Curated)
models.remove(ImageModel.Inpainting_Anime_v4_Full)

samplers = list(ImageSampler)
model_samplers = list(itertools.product(models, samplers))


test_results_dir = Path(__file__).parent.parent.parent / "test_results"


@pytest.mark.parametrize(
    "model_sampler",
    [
        pytest.param(e, marks=sampler_xfail)
        if e[1] in (ImageSampler.nai_smea, ImageSampler.plms, ImageSampler.k_dpm_adaptive)
        or e == (ImageModel.Anime_v3, ImageSampler.k_heun)
        or e == (ImageModel.Furry_v3, ImageSampler.nai_smea)
        or (
            e[0] in (ImageModel.Anime_v4_Curated, ImageModel.Anime_v4_Full)
            and e[1] in (ImageSampler.ddim, ImageSampler.nai_smea, ImageSampler.nai_smea_dyn, ImageSampler.plms)
        )
        else e
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
    if sampler is ImageSampler.ddim_v3 and model not in (ImageModel.Anime_v3, ImageModel.Furry_v3):
        return

    logger = api_handle.logger
    logger.info(f"Testing model {model} with sampler {sampler}")

    preset = ImagePreset.from_default_config(model)
    preset["sampler"] = sampler
    preset.copy()

    async for _, img in api.high_level.generate_image("1girl", model, preset):
        if test_results_dir.exists():
            (test_results_dir / f"image_{model.name}_{sampler.name}.png").write_bytes(img)


if __name__ == "__main__":

    async def main():
        async with API() as api:
            await test_samplers(api, (ImageModel.Anime_v3, ImageSampler.ddim_v3))

    asyncio.run(main())
