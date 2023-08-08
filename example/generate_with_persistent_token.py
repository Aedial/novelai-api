"""
{filename}
==============================================================================

Example of how to login on the provided account
"""

import asyncio
import os

from novelai_api import NovelAIAPI
from novelai_api.GlobalSettings import GlobalSettings
from novelai_api.Preset import Model, Preset


async def main():
    api = NovelAIAPI()

    token = os.environ.get("NAI_TOKEN")
    await api.high_level.login_with_token(token)

    model = Model.Kayra
    preset = Preset.from_default(model)
    globalsettings = GlobalSettings(num_logprobs=GlobalSettings.NO_LOGPROBS)

    print(await api.high_level.generate("***", model, preset, globalsettings))

    # see example/generate_text.py for more details


if __name__ == "__main__":
    asyncio.run(main())
