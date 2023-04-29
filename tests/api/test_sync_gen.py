"""
| Test if sync capabilities work without problem
| This test only checks if sync works, not if the result is right, it's the job of the other tests
"""

from novelai_api.GlobalSettings import GlobalSettings
from novelai_api.Preset import Model, Preset
from novelai_api.Tokenizer import Tokenizer
from novelai_api.utils import b64_to_tokens, decrypt_user_data
from tests.api.boilerplate import api_handle_sync, error_handler  # noqa: F401  # pylint: disable=W0611

prompt = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Aliquam at dolor dictum, interdum est sed, consequat arcu. Pellentesque in massa eget lorem fermentum placerat in pellentesque purus. Suspendisse potenti. Integer interdum, felis quis porttitor volutpat, est mi rutrum massa, venenatis viverra neque lectus semper metus. Pellentesque in neque arcu. Ut at arcu blandit purus aliquet finibus. Suspendisse laoreet risus a gravida semper. Aenean scelerisque et sem vitae feugiat. Quisque et interdum diam, eu vehicula felis. Ut tempus quam eros, et sollicitudin ligula auctor at. Integer at tempus dui, quis pharetra purus. Duis venenatis tincidunt tellus nec efficitur. Nam at malesuada ligula."  # noqa: E501  # pylint: disable=C0301
model = Model.Krake


@error_handler
async def test_is_reachable(api_handle_sync):  # noqa: F811  # pylint: disable=W0621
    assert await api_handle_sync.api.low_level.is_reachable() is True


@error_handler
async def test_download(api_handle_sync):  # noqa: F811  # pylint: disable=W0621
    key = api_handle_sync.encryption_key
    keystore = await api_handle_sync.api.high_level.get_keystore(key)
    modules = await api_handle_sync.api.high_level.download_user_modules()
    decrypt_user_data(modules, keystore)


@error_handler
async def test_generate(api_handle_sync):  # noqa: F811  # pylint: disable=W0621
    api = api_handle_sync.api

    logger = api.logger
    preset = Preset.from_default(model)

    logger.info("Using model %s, preset %s\n", model.value, preset.name)

    global_settings = GlobalSettings()
    gen = await api.high_level.generate(prompt, model, preset, global_settings)
    logger.info(gen)
    logger.info(Tokenizer.decode(model, b64_to_tokens(gen["output"])))
