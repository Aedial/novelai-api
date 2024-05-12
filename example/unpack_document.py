"""
{filename}
==============================================================================

Example of how to unpack the MessagePacked document field of the StoryContent data
"""

import asyncio
import base64
from pathlib import Path

from example.boilerplate import API
from novelai_api.msgpackr.novelai import NovelAiUnpacker


async def main():
    async with API() as api_handler:  # noqa: F841  # pylint: disable=W0612
        logger = api_handler.logger

        config_path = Path(__file__).parent.parent / "tests/api/sanity_text_sets"
        # load document data taken directly from a NovelAi sample record
        f = open(f"{config_path}/msgpackr/red-riding-hood.b64")
        b64_data = f.read()
        f.close()
        # decode data to retrieve raw byte array
        raw_data = base64.b64decode(b64_data)

        # instantiate the unpacker
        unpacker = NovelAiUnpacker()
        # unpack data into dict object
        content_doc = unpacker.unpack(raw_data)

        # dump unpacked data
        # logger.info(unpacker.stringify(content_doc))

        # The individual paragraph/sections stored for the story
        # this is the most recent version of the section and is already updated with
        # any edits made. Edits are described in detail in the history data, but are not
        # needed for the raw content of the story, only to see what was changed from the
        # original.
        sections = content_doc.get("sections")

        # The order the sections should be placed in when reconstituting the story
        order = content_doc.get("order")

        # a History of changes made to each section node
        # history = content_doc.get("history")

        # reconstitue sections into the story content data
        for key in order:
            section = sections.get(key)
            if section is not None:
                logger.info(section.get("text") + "\n")


if __name__ == "__main__":
    asyncio.run(main())
