from novelai_api.NovelAIError import NovelAIError
from novelai_api.FakeClientSession import FakeClientSession
from novelai_api.Keystore import Keystore
from novelai_api.SchemaValidator import SchemaValidator
from novelai_api.Preset import Preset, Model
from novelai_api.GlobalSettings import GlobalSettings
from novelai_api.BiasGroup import BiasGroup
from novelai_api.BanList import BanList
from novelai_api.utils import get_access_key, get_encryption_key, decrypt_data, encrypt_data

from json import dumps
from hashlib import sha256
from typing import Union, Dict, Tuple, List, Any, NoReturn, Optional, Iterable

class High_Level:
    _parent: "NovelAI_API"

    def __init__(self, parent: "NovelAI_API"):
        self._parent = parent

    async def register(self, recapcha: str, email: str, password: str, send_mail: bool = True, giftkey: Optional[str] = None) -> bool:
        """
        Register a new account

        :param recapcha: Recapcha of the NovelAI website
        :param email: Email of the account (username)
        :param password: Password of the account
        :param send_mail: Send the mail (hashed and used for recovery)
        :param giftkey: Giftkey

        :return: True if success
        """

        assert type(email) is str, f"Expected type 'str' for email, but got type '{type(email)}'"
        assert type(password) is str, f"Expected type 'str' for password, but got type '{type(password)}'"

        hashed_email = sha256(email.encode()).hexdigest() if send_mail else None
        key = get_access_key(email, password)
        return await self._parent.low_level.register(recapcha, key, hashed_email, giftkey)

    async def login(self, email: str, password: str) -> str:
        """
        Log in to the account

        :param email: Email of the account (username)
        :param password: Password of the account

        :return: User's access token
        """
        assert type(email) is str, f"Expected type 'str' for email, but got type '{type(email)}'"
        assert type(password) is str, f"Expected type 'str' for password, but got type '{type(password)}'"

        access_key = get_access_key(email, password)
        rsp = await self._parent.low_level.login(access_key)
        SchemaValidator.validate("schema_login", rsp)

        self._parent._session.headers["Authorization"] = f"Bearer {rsp['accessToken']}"

        return rsp["accessToken"]

    async def login_from_token(self, access_token: str) -> NoReturn:
        self._parent._session.headers["Authorization"] = f"Bearer {access_token}"

    async def get_keystore(self, key: bytes) -> Keystore:
        """
        Retrieve the keystore and decrypt it in a readable manner.
        The keystore is the mapping of meta -> encryption key of each object.
        If this function throws errors repeatedly at you,
        check your internet connection or the integrity of your keystore.
        Losing your keystore, or overwriting it means losing all content on the account.

        :param key: Account's encryption key
        
        :return: Keystore object
        """

        keystore = Keystore(await self._parent.low_level.get_keystore())
        keystore.decrypt(key)

        return keystore

    async def set_keystore(self, keystore: Keystore, key: bytes) -> bytes:
        keystore.encrypt(key)

        return await self._parent.low_level.set_keystore(keystore.data)

    async def download_user_stories(self) -> Dict[str, Dict[str, Union[str, int]]]:
        stories = await self._parent.low_level.download_objects("stories")
        SchemaValidator.validate("schema_encrypted_stories", stories)

        return stories["objects"]

    async def download_user_story_contents(self) -> Dict[str, Dict[str, Union[str, int]]]:
        story_contents = await self._parent.low_level.download_objects("storycontent")
        SchemaValidator.validate("schema_encrypted_stories", story_contents)

        return story_contents["objects"]

    async def download_user_presets(self) -> List[Dict[str, Union[str, int]]]:
        presets = await self._parent.low_level.download_objects("presets")
        SchemaValidator.validate("schema_encrypted_stories", presets)

        return presets["objects"]

    async def download_user_modules(self) -> List[Dict[str, Union[str, int]]]:
        modules = await self._parent.low_level.download_objects("aimodules")
        SchemaValidator.validate("schema_encrypted_stories", modules)

        return modules["objects"]

    async def download_user_shelves(self) -> List[Dict[str, Union[str, int]]]:
        modules = await self._parent.low_level.download_objects("shelf")
        SchemaValidator.validate("schema_encrypted_stories", modules)

        return modules["objects"]

    async def generate(self, input: Union[List[int], str], model: Model, preset: Preset,
                       global_settings: GlobalSettings, bad_words: Optional[BanList] = None,
                       biases: Optional[Iterable[BiasGroup]] = None, prefix: Optional[str] = None) -> Dict[str, Any]:
        assert preset is not None, "Uninitialized preset"
        assert preset.model == model, f"Preset {preset.name} (model {preset.model}) is not compatible with model {model}"

        preset_params = preset.to_settings()
        global_params = global_settings.to_settings()

        params = {}

        params.update(preset_params)
        params.update(global_params)

        params["prefix"] = "vanilla" if prefix is None else prefix

        if params["num_logprobs"] == GlobalSettings.NO_LOGPROBS:
            del params["num_logprobs"]

        if bad_words is not None:
            assert type(bad_words) is BanList, f"Expected type 'BanList' for bad_words, but got '{type(bad_words)}'"
            params["bad_words_ids"].extend(bad_words)

        if biases is not None:
            for i, bias in enumerate(biases):
                assert type(bias) is BiasGroup, f"Expected type 'BiasGroup' for item #{i} of biases, but got '{type(bias)}'"
                params["logit_bias_exp"].extend(bias)

        # Delete the options that return an unknown error (success status code, but server error)
        if params["repetition_penalty_slope"] == 0:
            del params["repetition_penalty_slope"]

        if not params["bad_words_ids"]:
            del params["bad_words_ids"]

        return await self._parent.low_level.generate(input, model, params)

    # TODO: encryption and upload