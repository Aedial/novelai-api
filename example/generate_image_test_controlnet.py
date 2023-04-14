import asyncio
import base64
import time

from boilerplate import API

from novelai_api.ImagePreset import ControlNetModel
from novelai_api.NovelAIError import NovelAIError


async def main():
    async with API() as api_handler:
        api = api_handler.api

        with open("image.png", "rb") as f:
            image = base64.b64encode(f.read()).decode()

        for controlnet in ControlNetModel:
            try:
                _, img = await api.low_level.generate_controlnet_mask(controlnet, image)
                with open(f"image_{controlnet.value}.png", "wb") as f:
                    f.write(img)

                print(f"Generated with {controlnet.value}")
                time.sleep(2)

            except NovelAIError as e:
                print(f"Failed with {controlnet.value}: {e}")
                time.sleep(5)


asyncio.run(main())
