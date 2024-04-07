"""
{filename}
==============================================================================

| Example of how to generate an image with inpainting
|
| The resulting image will be placed in a folder named "results"
"""

import asyncio
import base64
from pathlib import Path

from example.boilerplate import API
from novelai_api.ImagePreset import ImageGenerationType, ImageModel, ImagePreset


async def single_vibe():
    d = Path("results")
    d.mkdir(exist_ok=True)

    async with API() as api_handler:
        api = api_handler.api

        image = base64.b64encode((d / "image.png").read_bytes()).decode()

        model = ImageModel.Anime_v3

        preset = ImagePreset.from_default_config(model)
        preset.reference_image = image
        preset.reference_strength = 0.6
        preset.reference_information_extracted = 1.0
        preset.seed = 42

        async for _, img in api.high_level.generate_image("1girl", model, preset, ImageGenerationType.NORMAL):
            (d / "image_with_vibe.png").write_bytes(img)


async def multi_vibe():
    d = Path("results")
    d.mkdir(exist_ok=True)

    async with API() as api_handler:
        api = api_handler.api

        image1 = base64.b64encode((d / "image1.png").read_bytes()).decode()
        image2 = base64.b64encode((d / "image2.png").read_bytes()).decode()
        image3 = base64.b64encode((d / "image3.png").read_bytes()).decode()

        model = ImageModel.Anime_v3

        preset = ImagePreset.from_default_config(model)
        preset.reference_image_multiple = [image1, image2, image3]
        preset.reference_strength_multiple = [0.6, 0.6, 0.6]
        preset.reference_information_extracted_multiple = [1.0, 1.0, 1.0]
        preset.seed = 42

        async for _, img in api.high_level.generate_image("1girl", model, preset, ImageGenerationType.NORMAL):
            (d / "image_with_multivibe.png").write_bytes(img)


if __name__ == "__main__":
    asyncio.run(single_vibe())
    asyncio.run(multi_vibe())
