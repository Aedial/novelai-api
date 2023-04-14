from asyncio import run

from boilerplate import API

from novelai_api.ImagePreset import ImageModel, ImagePreset, ImageResolution, UCPreset


async def main():
    async with API() as api_handler:
        api = api_handler.api

        preset = ImagePreset()

        # multiple images

        # preset["n_samples"] = 4
        i = 0
        async for _, img in api.high_level.generate_image("1girl", ImageModel.Anime_Full, preset):
            with open(f"image_1_{i}.png", "wb") as f:
                f.write(img)

            i += 1

        # custom size

        preset["n_samples"] = 1
        preset["resolution"] = (128, 256)

        async for _, img in api.high_level.generate_image("1girl", ImageModel.Anime_Full, preset):
            with open("image_2.png", "wb") as f:
                f.write(img)

        # furry model

        preset["resolution"] = ImageResolution.Normal_Square
        # Furry model has no Bad Anatomy UC Preset
        preset["uc_preset"] = UCPreset.Preset_Low_Quality

        async for _, img in api.high_level.generate_image("female, species:human", ImageModel.Furry, preset):
            with open("image_3.png", "wb") as f:
                f.write(img)


run(main())
