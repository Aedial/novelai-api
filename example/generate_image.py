from sys import path
from os import environ as env
from os.path import join, abspath, dirname

path.insert(0, abspath(join(dirname(__file__), '..')))

import base64
from novelai_api import NovelAI_API
from novelai_api.ImagePreset import ImageModel, ImageResolution, UCPreset, ImagePreset
from aiohttp import ClientSession

from logging import Logger, StreamHandler
from asyncio import run

if "NAI_USERNAME" not in env or "NAI_PASSWORD" not in env:
    raise RuntimeError("Please ensure that NAI_USERNAME and NAI_PASSWORD are set in your environment")

username = env["NAI_USERNAME"]
password = env["NAI_PASSWORD"]

logger = Logger("NovelAI")
logger.addHandler(StreamHandler())


async def main():
    async with ClientSession() as session:
        api = NovelAI_API(session, logger = logger)

        login = await api.high_level.login(username, password)
        logger.info(login)

        preset = ImagePreset()

        # multiple images

        # WARNING: for whatever reason, n_samples doesn't work. I don't receive the event id 2,
        #          like I do in text streaming, so don't spend your Anlas in that !
        # preset["n_samples"] = 4

        i = 0
        async for img in api.high_level.generate_image("1girl", ImageModel.Anime_Full, preset):
            with open(f"image_1_{i}.png", "wb") as f:
                f.write(base64.b64decode(img))

            i += 1

        # custom size

        preset["n_samples"] = 1
        preset["resolution"] = (128, 256)

        async for img in api.high_level.generate_image("1girl", ImageModel.Anime_Full, preset):
            with open(f"image_2.png", "wb") as f:
                f.write(base64.b64decode(img))

        # furry model

        preset["resolution"] = ImageResolution.Normal_Square
        # Furry model has no Bad Anatomy UC Preset
        preset["uc_preset"] = UCPreset.Preset_Low_Quality

        async for img in api.high_level.generate_image("female, species:human", ImageModel.Furry, preset):
            with open(f"image_3.png", "wb") as f:
                f.write(base64.b64decode(img))

run(main())
