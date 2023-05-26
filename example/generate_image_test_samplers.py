"""
{filename}
==============================================================================

| Test on which sampler currently work. It will create one image per sampler
|
| The resulting images will be placed in a folder named "results"
"""

import asyncio
import time
from pathlib import Path

from example.boilerplate import API
from novelai_api.ImagePreset import ImageModel, ImagePreset, ImageSampler
from novelai_api.NovelAIError import NovelAIError


async def main():
    d = Path("results")
    d.mkdir(exist_ok=True)

    async with API() as api_handler:
        api = api_handler.api

        preset = ImagePreset()
        preset.seed = 42

        for sampler in ImageSampler:
            preset.sampler = sampler

            try:
                async for _, img in api.high_level.generate_image("1girl", ImageModel.Anime_Full, preset):
                    (d / f"image_{sampler.value}").write_bytes(img)

                print(f"Generated with {sampler.value}")
                time.sleep(2)

            except NovelAIError as e:
                print(f"Failed with {sampler.value}: {e}")
                time.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
