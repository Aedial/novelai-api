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
from novelai_api.ImagePreset import ImageModel, ImagePreset, ImageResolution, ImageSampler, UCPreset
from novelai_api.NovelAIError import NovelAIError


async def main():
    d = Path("results")
    d.mkdir(exist_ok=True)

    async with API() as api_handler:
        api = api_handler.api

        model = ImageModel.Anime_v3

        preset = ImagePreset.from_default_config(model)
        preset.resolution = ImageResolution.Normal_Portrait_v3
        preset.seed = 1796796669
        preset.scale = 5
        preset.uc_preset = UCPreset.Preset_None
        preset.uc = "{{{worst quality, low quality, bad fingers}}},"

        preset.quality_toggle = False

        prompt = (
            "1girl, smile to viewer, sunny day, frilly white dress, lens flare, sunrays, "
            "{{detailed fingers, bold outline}}, best quality, amazing quality, very aesthetic, absurdres"
        )
        samplers = [ImageSampler.ddim]

        for sampler in samplers:
            preset.sampler = sampler

            try:
                async for _, img in api.high_level.generate_image(prompt, model, preset):
                    (d / f"image_{sampler.value}").write_bytes(img)

                print(f"Generated with {sampler.value}")
                time.sleep(2)

            except NovelAIError as e:
                print(f"Failed with {sampler.value}: {e}")
                time.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
