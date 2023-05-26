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

        image = base64.b64encode((d / "image.png").read_bytes()).decode()

        preset = ImagePreset()
        preset.noise = 0.1
        # note that steps = 28, not 50, which mean strength needs to be adjusted accordingly
        preset.strength = 0.5
        preset.image = image
        preset.seed = 42

        async for _, img in api.high_level.generate_image(
            "1girl", ImageModel.Anime_Full, preset, ImageGenerationType.IMG2IMG
        ):
            (d / "image_with_img2img.png").write_bytes(img)


if __name__ == "__main__":
    asyncio.run(main())
