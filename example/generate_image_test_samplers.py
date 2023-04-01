import time
from asyncio import run

from boilerplate import API

from novelai_api.ImagePreset import ImageModel, ImagePreset, ImageSampler
from novelai_api.NovelAIError import NovelAIError


async def main():
    async with API() as api_handler:
        api = api_handler.api
        api.BASE_ADDRESS = api.BASE_ADDRESS.replace("api", "api2")

        preset = ImagePreset()

        for sampler in ImageSampler:
            preset["sampler"] = sampler

            try:
                async for img in api.high_level.generate_image("1girl", ImageModel.Anime_Full, preset):
                    with open(f"image_{sampler.value}.png", "wb") as f:
                        f.write(img)

                print(f"Generated with {sampler.value}")
                time.sleep(2)

            except NovelAIError as e:
                print(f"Failed with {sampler.value}: {e}")
                time.sleep(5)


run(main())
