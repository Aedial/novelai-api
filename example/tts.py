from sys import path
from os import environ as env
from os.path import join, abspath, dirname

path.insert(0, abspath(join(dirname(__file__), '..')))

from novelai_api import NovelAI_API
from aiohttp import ClientSession

from logging import Logger, StreamHandler
from asyncio import run

if "NAI_USERNAME" not in env or "NAI_PASSWORD" not in env:
    raise RuntimeError("Please ensure that NAI_USERNAME and NAI_PASSWORD are set in your environment")

username = env["NAI_USERNAME"]
password = env["NAI_PASSWORD"]

logger = Logger("NovelAI")
logger.addHandler(StreamHandler())

#tts_file = "tts.webm"
tts_file = "tts.mp3"

async def main():
    async with ClientSession() as session:
        api = NovelAI_API(session, logger = logger)
        logger.info(await api.high_level.login(username, password))

        text = """Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Purus ut faucibus pulvinar elementum integer enim neque volutpat. Sit amet massa vitae tortor condimentum lacinia. Vitae tempus quam pellentesque nec. Eu tincidunt tortor aliquam nulla facilisi cras fermentum odio. Vel risus commodo viverra maecenas accumsan lacus vel. Amet luctus venenatis lectus magna fringilla urna porttitor rhoncus dolor. Risus quis varius quam quisque. Rutrum tellus pellentesque eu tincidunt tortor aliquam nulla. Cras pulvinar mattis nunc sed blandit libero volutpat. Velit euismod in pellentesque massa placerat duis. Quam id leo in vitae turpis massa. Dui accumsan sit amet nulla facilisi.

Justo eget magna fermentum iaculis eu non diam phasellus vestibulum. Enim nunc faucibus a pellentesque sit. Lectus nulla at volutpat diam ut. Pretium fusce id velit ut. A scelerisque purus semper eget duis at tellus. Nibh nisl condimentum id venenatis a condimentum vitae. Ut sem viverra aliquet eget sit amet tellus cras. Suspendisse sed nisi lacus sed viverra. Volutpat consequat mauris nunc congue nisi. Ornare lectus sit amet est. Ac turpis egestas integer eget aliquet nibh praesent. Fusce id velit ut tortor pretium."

Diam sit amet nisl suscipit adipiscing bibendum est ultricies integer. Non curabitur gravida arcu ac tortor dignissim convallis. Porttitor rhoncus dolor purus non enim praesent elementum facilisis. Mauris nunc congue nisi vitae suscipit tellus mauris a. Arcu dui vivamus arcu felis bibendum ut tristique et egestas. Faucibus nisl tincidunt eget nullam non nisi est sit amet. Enim facilisis gravida neque convallis a. Amet nisl purus in mollis nunc sed id semper risus. In pellentesque massa placerat duis ultricies lacus sed. Convallis posuere morbi leo urna molestie at. Aliquam sem et tortor consequat id porta nibh venenatis. Luctus venenatis lectus magna fringilla urna porttitor rhoncus. Sit amet consectetur adipiscing elit. Consectetur adipiscing elit ut aliquam purus. Porttitor massa id neque aliquam vestibulum morbi blandit cursus risus. Nulla aliquet porttitor lacus luctus accumsan tortor. Elit eget gravida cum sociis."

Eleifend quam adipiscing vitae proin sagittis nisl rhoncus. Vitae proin sagittis nisl rhoncus mattis rhoncus urna. Et egestas quis ipsum suspendisse. Amet facilisis magna etiam tempor orci eu lobortis elementum. Penatibus et magnis dis parturient. Posuere morbi leo urna molestie at elementum eu. Duis convallis convallis tellus id interdum velit laoreet. Eu turpis egestas pretium aenean pharetra magna. Ornare aenean euismod elementum nisi quis eleifend quam adipiscing vitae. Vitae purus faucibus ornare suspendisse sed nisi lacus sed viverra. Cursus vitae congue mauris rhoncus aenean vel elit scelerisque mauris. Urna et pharetra pharetra massa massa ultricies mi. Sagittis eu volutpat odio facilisis mauris sit amet massa. Facilisi etiam dignissim diam quis enim lobortis scelerisque. Phasellus vestibulum lorem sed risus ultricies tristique nulla aliquet. Orci sagittis eu volutpat odio facilisis mauris sit. A diam sollicitudin tempor id eu. Ultrices neque ornare aenean euismod elementum nisi quis eleifend. Diam sit amet nisl suscipit adipiscing. Fames ac turpis egestas maecenas pharetra convallis posuere."

Egestas sed tempus urna et pharetra. Blandit turpis cursus in hac habitasse platea dictumst. Nisi quis eleifend quam adipiscing vitae proin sagittis nisl. Eu ultrices vitae auctor eu augue ut lectus. Eget felis eget nunc lobortis. Purus in massa tempor nec. Vitae elementum curabitur vitae nunc sed. Molestie nunc non blandit massa enim nec dui nunc mattis. Diam maecenas sed enim ut sem viverra aliquet. Ipsum a arcu cursus vitae congue. Interdum varius sit amet mattis vulputate enim nulla aliquet porttitor. Donec pretium vulputate sapien nec sagittis aliquam. Fermentum posuere urna nec tincidunt praesent semper feugiat. Vehicula ipsum a arcu cursus vitae congue mauris rhoncus. Erat pellentesque adipiscing commodo elit at imperdiet dui. At ultrices mi tempus imperdiet nulla malesuada pellentesque elit eget. Ultrices mi tempus imperdiet nulla malesuada.
"""
        voice = "Aini"
        seed = 42
        opus = False
#        opus = True
#        version = "v1"
        version = "v2"

        logger.info(f"Generating a tts voice for {len(text)} characters of text")

        tts = await api.low_level.generate_voice(text, voice, seed, opus, version)
        with open(tts_file, "wb") as f:
            f.write(tts)

        logger.info(f"TTS saved in {tts_file}")

run(main())
