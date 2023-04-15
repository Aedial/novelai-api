import time
from asyncio import run
from pathlib import Path

from boilerplate import API

from novelai_api.ImagePreset import ImageModel, ImagePreset, ImageSampler
from novelai_api.NovelAIError import NovelAIError


async def main():
    d = Path("results")
    d.mkdir(exist_ok=True)

    async with API() as api_handler:
        api = api_handler.api

        preset = ImagePreset()

        for sampler in ImageSampler:
            preset.sampler = sampler

            try:
                async for _, img in api.high_level.generate_image("1girl", ImageModel.Anime_Full, preset):
                    with open(d / f"image_{sampler.value}.png", "wb") as f:
                        f.write(img)

                print(f"Generated with {sampler.value}")
                time.sleep(2)

            except NovelAIError as e:
                print(f"Failed with {sampler.value}: {e}")
                time.sleep(5)


run(main())
