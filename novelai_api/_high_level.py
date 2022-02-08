from json import dumps
from novelai_api.NovelAIError import NovelAIError
from novelai_api.FakeClientSession import FakeClientSession
from novelai_api.Keystore import Keystore
from novelai_api.SchemaValidator import SchemaValidator
from novelai_api.Preset import Preset, Model
from novelai_api.GlobalSettings import GlobalSettings
from novelai_api.BiasGroup import BiasGroup
from novelai_api.BanList import BanList
from novelai_api.utils import get_access_key, decompress_user_data, compress_user_data, decrypt_user_data, encrypt_user_data

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

    async def login_from_token(self, access_key: str) -> NoReturn:
        rsp = await self._parent.low_level.login(access_key)
        SchemaValidator.validate("schema_login", rsp)

        self._parent._session.headers["Authorization"] = f"Bearer {rsp['accessToken']}"

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

    async def upload_user_content(self, data: Dict[str, Any], encrypt: bool = False, keystore: Optional[Keystore] = None) -> bool:
        """
        Upload an user content. If it has been decrypted with decrypt_user_data,
        it should be re-encrypted with encrypt_user_data, even if the decryption failed

        :param data: Object to upload
        :param encrypt: Encrypt/compress the data if True and not already encrypted
        :param keystore: Keystore to encrypt data if encrypt is True

        :return: True if the upload succeeded, False otherwise
        """

        object_id = data["id"]
        object_type = data["type"]
        object_meta = data["meta"]
        object_data = data["data"]

        if encrypt:
            if object_type in ("stories", "storycontent", "aimodules", "shelf"):
                assert keystore is not None, "Keystore is not set, cannot encrypt data"
                encrypt_user_data(data, keystore)
            elif object_type in ("presets", ):
                compress_user_data(data)

        # clean data introduced by decrypt_user_data
        # this step should have been done in encrypt_user_data, but the user could have not called it
        for key in ("nonce", "compressed", "decrypted"):
            if key in object_data:
                self._parent.logger.warn(f"Data {key} left in object '{object_type}' of id '{object_id}'")
                del object_data[key]

        return await self._parent.low_level.upload_object(object_type, object_id, object_meta, object_data)

    async def upload_user_contents(self, datas: Iterable[Dict[str, Any]]) -> List[Tuple[str, Optional[NovelAIError]]]:
        """
        Upload multiple user contents. If the content has been decrypted with decrypt_user_data,
        it should be re-encrypted with encrypt_user_data, even if the decryption failed

        :param datas: Objects to upload

        :return: A list of (id, error) of all the objects that failed to be uploaded
        """

        status = []

        for data in datas:
            try:
                success = await self.upload_user_content(data)
                if not success:
                    status.append((data["id"], None))
            except NovelAIError as e:
                status.append((data["id"], e))

        return status

    async def generate(self, input: Union[List[int], str], model: Model, preset: Preset,
                       global_settings: GlobalSettings, bad_words: Optional[Union[Iterable[BanList], BanList]] = None,
                       biases: Optional[Union[Iterable[BiasGroup], BiasGroup]] = None, prefix: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate content from an AI on the NovelAI server

        :param input: Context to give to the AI (raw text or list of tokens)
        :param model: Model to use for the AI
        :param preset: Preset to use for the generation settings
        :param global_settings: Global settings (used for generation)
        :param bad_words: Tokens to ban for this generation
        :param biases: Tokens to bias (up or down) for this generation
        :param prefix: Module to use for this generation

        :return: Content that has been generated
        """

        assert preset is not None, "Uninitialized preset"
        assert preset.model == model, f"Preset {preset.name} (model {preset.model}) is not compatible with model {model}"

        preset_params = preset.to_settings()
        global_params = global_settings.to_settings(model)

        params = {}

        params.update(preset_params)
        params.update(global_params)

        params["prefix"] = "vanilla" if prefix is None else prefix

        if params["num_logprobs"] == GlobalSettings.NO_LOGPROBS:
            del params["num_logprobs"]

        if bad_words is not None:
            if type(bad_words) is BanList:
                bad_words = [bad_words]

            for i, bad_word in enumerate(bad_words):
                assert type(bad_word) is BanList, f"Expected type 'BanList' for item #{i} of bad_words, but got '{type(bad_word)}'"
                params["bad_words_ids"].extend(bad_word.get_tokenized_banlist(model))

        if biases is not None:
            if type(biases) is BiasGroup:
                biases = [biases]

            for i, bias in enumerate(biases):
                assert type(bias) is BiasGroup, f"Expected type 'BiasGroup' for item #{i} of biases, but got '{type(bias)}'"
                params["logit_bias_exp"].extend(bias.get_tokenized_biases(model))

        # Delete the options that return an unknown error (success status code, but server error)
        if "repetition_penalty_slope" in params and params["repetition_penalty_slope"] == 0:
            del params["repetition_penalty_slope"]

        if not params["bad_words_ids"]:
            del params["bad_words_ids"]

        return await self._parent.low_level.generate(input, model, params)

    # TODO: encryption and upload