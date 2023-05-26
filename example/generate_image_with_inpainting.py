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


async def main():
    d = Path("results")
    d.mkdir(exist_ok=True)

    async with API() as api_handler:
        api = api_handler.api

        image = base64.b64encode((d / "image.png").read_bytes()).decode()
        mask = base64.b64encode((d / "inpainting_mask.png").read_bytes()).decode()

        preset = ImagePreset()
        preset.image = image
        preset.mask = mask
        preset.seed = 42

        async for _, img in api.high_level.generate_image(
            "1girl", ImageModel.Inpainting_Anime_Full, preset, ImageGenerationType.INPAINTING
        ):
            (d / "image_with_inpainting.png").write_bytes(img)


if __name__ == "__main__":
    asyncio.run(main())
