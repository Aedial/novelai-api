from asyncio import run

from boilerplate import API, dumps

from novelai_api.ImagePreset import ImageModel

tags = ["gi", "bo", "scal", "cre"]


async def main():
    async with API() as api_handler:
        api = api_handler.api
        logger = api_handler.logger

        for tag in tags:
            for model in (ImageModel.Anime_Full, ImageModel.Furry):
                e = await api.low_level.suggest_tags(tag, model)
                logger.info(f"Tag: {tag}, Model: {model}")
                logger.info(dumps(e))


run(main())
