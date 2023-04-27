"""
{filename}
==============================================================================

| Example of how to upscale an image
|
| It expects an image "results/image.png" to exist and will generate the resulting masks in this same folder
| The image should be 512x768 by default, modify :code:`image_size` to change it
"""

import asyncio
import base64
import time
from pathlib import Path

from example.boilerplate import API
from novelai_api.NovelAIError import NovelAIError


async def main():
    d = Path("results")
    d.mkdir(exist_ok=True)

    image_size = (512, 768)

    async with API() as api_handler:
        api = api_handler.api

        with open(d / "image.png", "rb") as f:
            image = base64.b64encode(f.read()).decode()

        # disable the type check on scale in _low_level.py to check on float values
        for scale in (2, 4):
            try:
                _, img = await api.low_level.upscale_image(image, *image_size, scale)
                with open(f"image_upscaled_{scale}.png", "wb") as f:
                    f.write(img)

                print(f"Generated upscale {scale}")
                time.sleep(2)

            except NovelAIError as e:
                print(f"Failed upscale {scale}: {e}")
                time.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
