import asyncio
import base64
import time

from boilerplate import API

from novelai_api.NovelAIError import NovelAIError


async def main():
    async with API() as api_handler:
        api = api_handler.api
        api.BASE_ADDRESS = api.BASE_ADDRESS.replace("api", "api2")

        with open("image.png", "rb") as f:
            image = base64.b64encode(f.read()).decode()

        # disable the type check on scale in _low_level.py to check on float values
        for scale in (2, 2.5, 3, 3.5, 4, 4.5, 5):
            try:
                img = await api.low_level.upscale_image(image, 512, 768, scale)
                with open(f"image_upscaled_{scale}.png", "wb") as f:
                    f.write(img)

                print(f"Generated upscale {scale}")
                time.sleep(2)

            except NovelAIError as e:
                print(f"Failed upscale {scale}: {e}")
                time.sleep(5)


asyncio.run(main())
