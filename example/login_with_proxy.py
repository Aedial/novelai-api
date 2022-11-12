from asyncio import run

from boilerplate import API


async def main():
    api_inst = API()

    # insert proxy address here
    api_inst.api.proxy = None
    # insert proxy auth here
    api_inst.api.proxy_auth = None

    async with api_inst as api_handler:  # noqa: F841  # pylint: disable=W0612
        pass


run(main())
