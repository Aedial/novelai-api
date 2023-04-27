"""
{filename}
==============================================================================

| Example of how to query the controlnet masks for an image
|
| It expects an image "results/image.png" to exist and will generate the resulting masks in this same folder
| NOTE: Currently the returned mask is wrong due to an image conversion in frontend (see :issue:`15`)
"""

import asyncio
import base64
import time
from pathlib import Path

from example.boilerplate import API
from novelai_api.ImagePreset import ControlNetModel
from novelai_api.NovelAIError import NovelAIError


async def main():
    d = Path("results")
    d.mkdir(exist_ok=True)

    async with API() as api_handler:
        api = api_handler.api

        with open(d / "image.png", "rb") as f:
            image = base64.b64encode(f.read()).decode()

        for controlnet in ControlNetModel:
            try:
                _, img = await api.low_level.generate_controlnet_mask(controlnet, image)
                with open(d / f"image_{controlnet.value}.png", "wb") as f:
                    f.write(img)

                print(f"Generated with {controlnet.value}")
                time.sleep(2)

            except NovelAIError as e:
                print(f"Failed with {controlnet.value}: {e}")
                time.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
