"""
{filename}
==============================================================================

| Example of how to generate an image with img2img
|
| The resulting image will be placed in a folder named "results"
"""

import asyncio
import base64
from pathlib import Path

from example.boilerplate import API
from novelai_api.ImagePreset import ImageGenerationType, ImageModel, ImagePreset


async def main():
    d = Path("results")
    d.mkdir(exist_ok=True)

    async with API() as api_handler:
        api = api_handler.api

        with open(d / "image.png", "rb") as f:
            image = base64.b64encode(f.read()).decode()

        preset = ImagePreset()
        preset.noise = 0.1
        # note that steps = 28, not 50, which mean strength needs to be adjusted accordingly
        preset.strength = 0.5
        preset.image = image

        async for _, img in api.high_level.generate_image(
            "1girl", ImageModel.Anime_Full, preset, ImageGenerationType.IMG2IMG
        ):
            with open(d / "image_with_img2img.png", "wb") as f:
                f.write(img)


if __name__ == "__main__":
    asyncio.run(main())
