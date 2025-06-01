"""
{filename}
==============================================================================

| Example of how to generate an image
|
| The resulting images will be placed in a folder named "results"
"""

import asyncio
from pathlib import Path

from example.boilerplate import API
from novelai_api.ImagePreset import ImageModel, ImagePreset


async def main():
    d = Path("results")
    d.mkdir(exist_ok=True)

    async with API() as api_handler:
        api = api_handler.api

        model = ImageModel.Anime_v4_Curated
        # model = ImageModel.Anime_v4_Full
        # model = ImageModel.Anime_v45_Full
        # model = ImageModel.Anime_v45_Curated

        preset = ImagePreset.from_default_config(model)
        preset.seed = 42

        # NOTE: Order matters! It will give slightly different results if you change the order of the characters.
        # even though we give positions, the model can ignore them
        preset.characters = [
            # prompt, uc, position
            {"prompt": "boy"},  # default position is "C3"
            {"prompt": "girl", "position": "A3"},
        ]

        prompt = "1girl, 1boy"
        async for _, img in api.high_level.generate_image(prompt, model, preset):
            (d / f"image_v4.png").write_bytes(img)


if __name__ == "__main__":
    asyncio.run(main())
