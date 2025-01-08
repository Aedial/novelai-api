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
from novelai_api.ImagePreset import ImageModel, ImagePreset, UCPreset


async def main():
    d = Path("results")
    d.mkdir(exist_ok=True)

    async with API() as api_handler:
        api = api_handler.api

        model = ImageModel.Anime_v4_preview
        preset = ImagePreset.from_default_config(model)
        preset.seed = 42
        preset.uc_preset = UCPreset.Preset_Heavy
        preset.quality_toggle = False

        # even though we give positions, the model can ignore them
        preset.characters = [
            # prompt, uc, position
            {"prompt": "girl", "position": "A3"},
            {"prompt": "boy"},  # default position is "C3"
        ]

        # "1girl, 1boy" + quality tags without "rating:general"
        prompt = "1girl, 1boy, best quality, very aesthetic, absurdres"
        async for _, img in api.high_level.generate_image(prompt, model, preset):
            (d / f"image_v4.png").write_bytes(img)


if __name__ == "__main__":
    asyncio.run(main())
