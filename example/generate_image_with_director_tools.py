"""
{filename}
==============================================================================

| Example of how to generate an image
|
| The resulting images will be placed in a folder named "results"
"""

import asyncio
import time
from pathlib import Path

from example.boilerplate import API
from novelai_api.DirectorToolsPreset import DirectorToolsPreset


async def main():
    d = Path("results")
    d.mkdir(exist_ok=True)

    async with API() as api_handler:
        api = api_handler.api

        preset = DirectorToolsPreset.from_image(d / "image_v3.png")
        preset.prompt = ":3"
        preset.emotion = "happy"

        funcs = {
            # WARNING: this function takes Anlas at any size and is fairly expensive
            # "remove_background": api.high_level.remove_background,
            "lineart": api.high_level.line_art,
            "sketch": api.high_level.sketch,
            "colorize": api.high_level.colorize,
            "emotion": api.high_level.emotion,
            "declutter": api.high_level.declutter,
        }

        for func_name, func in funcs.items():
            image = await func(preset)  # [0] is the name, [1] is the image
            (d / f"image_with_tool_{func_name}.png").write_bytes(image[1])

            time.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
