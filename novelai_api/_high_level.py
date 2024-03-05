import json
from hashlib import sha256
from typing import Any, AsyncIterable, Dict, Iterable, List, Optional, Tuple, Type, Union

from novelai_api.BanList import BanList
from novelai_api.BiasGroup import BiasGroup
from novelai_api.GlobalSettings import GlobalSettings
from novelai_api.ImagePreset import ImageGenerationType, ImageModel, ImagePreset
from novelai_api.Keystore import Keystore
from novelai_api.NovelAIError import NovelAIError
from novelai_api.Preset import Model, Preset
from novelai_api.python_utils import assert_type
from novelai_api.Tokenizer import Tokenizer
from novelai_api.utils import compress_user_data, encrypt_user_data, get_access_key


class HighLevel:
    """
    High level API for NovelAI. This class is not meant to be used directly,
    but rather through :attr:`NovelAIAPI.high_level <novelai_api.NovelAI_API.NovelAIAPI.high_level>`.

    The most relevant methods are:

    * :meth:`login <novelai_api._high_level.HighLevel.login>`
    * :meth:`generate <novelai_api._high_level.HighLevel.generate>`
    * :meth:`generate_image <novelai_api._high_level.HighLevel.generate_image>`
    """

    _parent: "NovelAIAPI"  # noqa: F821

    def __init__(self, parent: "NovelAIAPI"):  # noqa: F821
        self._parent = parent

    async def register(
        self,
        recapcha: str,
        email: str,
        password: str,
        send_mail: bool = True,
        giftkey: Optional[str] = None,
    ) -> bool:
        """
        Register a new account

        :param recapcha: Recapcha of the NovelAI website
        :param email: Email of the account (username)
        :param password: Password of the account
        :param send_mail: Send the mail (hashed and used for recovery)
        :param giftkey: Giftkey

        :return: True if success
        """

        assert_type(str, email=email)

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

        access_key = get_access_key(email, password)
        rsp = await self._parent.low_level.login(access_key)

        self._parent.headers["Authorization"] = f"Bearer {rsp['accessToken']}"

        return rsp["accessToken"]

    async def login_with_token(self, access_token: str):
        """
        Log in with the access token, instead of email and password

        :param access_token: Access token of the account (persistent token or gotten from login)
        """

        self._parent.headers["Authorization"] = f"Bearer {access_token}"

    async def login_from_key(self, access_key: str):
        """
        Log in with the access key, instead of email and password

        :param access_key: Access key of the account (pre-computed via email and password)

        :return: User's access token
        """

        rsp = await self._parent.low_level.login(access_key)

        self._parent.headers["Authorization"] = f"Bearer {rsp['accessToken']}"

        return rsp["accessToken"]

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
        """
        Encrypt and upload the keystore.

        The keystore is the mapping of meta -> encryption key of each object.
        If this function throws errors repeatedly at you,
        check your internet connection or the integrity of your keystore.
        Losing your keystore, or overwriting it means losing all content on the account.

        :param keystore: Keystore object to upload
        :param key: Account's encryption key

        :return: raw data of the serialized Keystore object
        """

        keystore.encrypt(key)

        return await self._parent.low_level.set_keystore(keystore.data)

    async def download_user_stories(self) -> List[Dict[str, Dict[str, Union[str, int]]]]:
        """
        Download all the objects of type 'stories' stored on the account
        """

        stories = await self._parent.low_level.download_objects("stories")

        return stories["objects"]

    async def download_user_story_contents(
        self,
    ) -> List[Dict[str, Dict[str, Union[str, int]]]]:
        """
        Download all the objects of type 'storycontent' stored on the account
        """

        story_contents = await self._parent.low_level.download_objects("storycontent")

        return story_contents["objects"]

    async def download_user_presets(self) -> List[Dict[str, Union[str, int]]]:
        """
        Download all the objects of type 'presets' stored on the account
        """

        presets = await self._parent.low_level.download_objects("presets")

        return presets["objects"]

    async def download_user_modules(self) -> List[Dict[str, Union[str, int]]]:
        """
        Download all the objects of type 'aimodules' stored on the account
        """

        modules = await self._parent.low_level.download_objects("aimodules")

        return modules["objects"]

    async def download_user_shelves(self) -> List[Dict[str, Union[str, int]]]:
        """
        Download all the objects of type 'shelf' stored on the account
        """

        modules = await self._parent.low_level.download_objects("shelf")

        return modules["objects"]

    async def upload_user_content(
        self,
        data: Dict[str, Any],
        encrypt: bool = False,
        keystore: Optional[Keystore] = None,
    ) -> bool:
        """
        Upload user content

        :param data: Object to upload
        :param encrypt: Re-encrypt/re-compress the data, if True
        :param keystore: Keystore to encrypt the data, if encrypt is True

        :return: True if the upload succeeded, False otherwise
        """

        object_id = data["id"]
        object_type = data["type"]
        object_meta = data["meta"]
        object_data = data["data"]

        if encrypt:
            if object_type in ("stories", "storycontent", "aimodules"):
                if keystore is None:
                    raise ValueError("'keystore' is not set, cannot encrypt data")

                encrypt_user_data(data, keystore)
            elif object_type in ("shelf", "presets"):
                compress_user_data(data)

        # clean data introduced by decrypt_user_data
        # this step should have been done in encrypt_user_data, but the user could have not called it
        for key in ("nonce", "compressed", "decrypted"):
            if key in object_data:
                self._parent.logger.warning(f"Data {key} left in object '{object_type}' of id '{object_id}'")
                del object_data[key]

        return await self._parent.low_level.upload_object(object_type, object_id, object_meta, object_data)

    async def upload_user_contents(
        self,
        datas: Iterable[Dict[str, Any]],
        encrypt: bool = False,
        keystore: Optional[Keystore] = None,
    ) -> List[Tuple[str, Optional[NovelAIError]]]:
        """
        Upload multiple user contents. If the content has been decrypted with decrypt_user_data,
        it should be re-encrypted with encrypt_user_data, even if the decryption failed

        :param datas: Objects to upload
        :param encrypt: Re-encrypt/re-compress the data, if True
        :param keystore: Keystore to encrypt the data, if encrypt is True

        :return: A list of (id, error) of all the objects that failed to be uploaded
        """

        status = []

        for data in datas:
            try:
                success = await self.upload_user_content(data, encrypt, keystore)

                if not success:
                    status.append((data["id"], None))
            except NovelAIError as e:
                status.append((data["id"], e))

        return status

    async def _generate(
        self,
        prompt: Union[List[int], str],
        model: Model,
        preset: Preset,
        global_settings: GlobalSettings,
        bad_words: Optional[Union[Iterable[BanList], BanList]] = None,
        biases: Optional[Union[Iterable[BiasGroup], BiasGroup]] = None,
        prefix: Optional[str] = None,
        stop_sequences: Optional[Union[List[int], str]] = None,
        stream: bool = False,
        **kwargs,
    ):
        """
        Generate text with streaming support.

        :param prompt: Context to give to the AI (raw text or list of tokens)
        :param model: Model to use for the AI
        :param preset: Preset to use for the generation settings
        :param global_settings: Global settings (used for generation)
        :param bad_words: Tokens to ban for this generation
        :param biases: Tokens to bias (up or down) for this generation
        :param prefix: Module to use for this generation (see :ref:`list of modules <list-of-modules>`)
        :param stop_sequences: List of strings or tokens to stop the generation at
        :param stream: Use data streaming for the response
        :param kwargs: Additional parameters to pass to the requests. Can also be used to overwrite existing parameters

        :return: Content that has been generated
        """

        if preset is None:
            raise ValueError("Uninitialized preset")
        if preset.model is not model:
            raise ValueError(f"Preset '{preset.name}' (model {preset.model}) is not compatible with model {model}")

        preset_params = preset.to_settings()

        # special case for repetition penalty whitelist, as it belongs to global settings but is stored in preset files
        repetition_penalty_default_whitelist = global_settings.rep_pen_whitelist
        if preset_params.pop("repetition_penalty_default_whitelist", False):
            global_settings.rep_pen_whitelist = True

        global_params = global_settings.to_settings(model)
        global_settings.rep_pen_whitelist = repetition_penalty_default_whitelist

        params = {
            "repetition_penalty_whitelist": list(
                set(
                    item
                    for sublist in [
                        global_params.pop("repetition_penalty_whitelist", []),
                        preset_params.pop("repetition_penalty_whitelist", []),
                    ]
                    for inner_list in sublist
                    for item in inner_list
                )
            )
        }

        params.update(preset_params)
        params.update(global_params)
        params.update(kwargs)

        # adjust repetition penalty value for Sigurd and Euterpe
        if model in (Model.Sigurd, Model.Euterpe) and "repetition_penalty" in params:
            rep_pen = params["repetition_penalty"]
            params["repetition_penalty"] = (0.525 * (rep_pen - 1) / 7) + 1

        # module
        params["prefix"] = "vanilla" if prefix is None else prefix

        # bans and biases
        for k, v, c in (("bad_words_ids", bad_words, BanList), ("logit_bias_exp", biases, BiasGroup)):
            k: str
            v: Union[Iterable[BanList], Iterable[BiasGroup], BanList, BiasGroup, None]
            c: Union[Type[BanList], Type[BiasGroup]]

            if v is not None:
                if isinstance(v, c):
                    v = [v]

                for i, obj in enumerate(v):
                    if not isinstance(obj, c):
                        raise ValueError(f"Expected type '{c}' for item #{i} of '{k}', but got '{type(obj)}'")

                    params[k].extend(obj.get_tokenized_entries(model))

            if k in params and not params[k]:
                del params[k]

        # stop sequences
        if stop_sequences is not None:
            if not isinstance(stop_sequences, list):
                raise ValueError(f"Expected type 'list' for 'stop_sequences', but got '{type(stop_sequences)}'")

            for i, obj in enumerate(stop_sequences):
                if isinstance(obj, str):
                    stop_sequences[i] = Tokenizer.encode(model, obj)
                elif not isinstance(obj, list):
                    raise ValueError(
                        f"Expected type 'str' or 'list' for item #{i} of 'stop_sequences', " f"but got '{type(obj)}'"
                    )

            params["stop_sequences"] = stop_sequences

        async for i in self._parent.low_level.generate(prompt, model, params, stream):
            yield i

    async def generate(
        self,
        prompt: Union[List[int], str],
        model: Model,
        preset: Preset,
        global_settings: GlobalSettings,
        bad_words: Optional[Union[Iterable[BanList], BanList]] = None,
        biases: Optional[Union[Iterable[BiasGroup], BiasGroup]] = None,
        prefix: Optional[str] = None,
        stop_sequences: Optional[Union[List[int], str]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate text. The b64-encoded text is returned at once, when generation is finished.
        To decode the text, the :meth:`novelai_api.utils.b64_to_tokens`
        and :meth:`novelai_api.Tokenizer.Tokenizer.decode` methods should be used.

        As the model accepts a complete prompt, the context building must be done before calling this function.
        Any content going beyond the tokens limit will be truncated, starting from the top.


        :param prompt: Context to give to the AI (raw text or list of tokens)
        :param model: Model to use for the AI
        :param preset: Preset to use for the generation settings
        :param global_settings: Global settings (used for generation)
        :param bad_words: Tokens to ban for this generation
        :param biases: Tokens to bias (up or down) for this generation
        :param prefix: Module to use for this generation (see :ref:`list of modules <list-of-modules>`)
        :param stop_sequences: List of strings or tokens to stop the generation at
        :param kwargs: Additional parameters to pass to the requests. Can also be used to overwrite existing parameters

        :return: Content that has been generated
        """

        async for e in self._generate(
            prompt,
            model,
            preset,
            global_settings,
            bad_words,
            biases,
            prefix,
            stop_sequences,
            False,
            **kwargs,
        ):
            return e

    async def generate_stream(
        self,
        prompt: Union[List[int], str],
        model: Model,
        preset: Preset,
        global_settings: GlobalSettings,
        bad_words: Optional[Union[Iterable[BanList], BanList]] = None,
        biases: Optional[Union[Iterable[BiasGroup], BiasGroup]] = None,
        prefix: Optional[str] = None,
        stop_sequences: Optional[Union[List[int], str]] = None,
        **kwargs,
    ) -> AsyncIterable[Dict[str, Any]]:
        """
        Generate text. The text is returned one token at a time, as it is generated.

        As the model accepts a complete prompt, the context building must be done before calling this function.
        Any content going beyond the tokens limit will be truncated, starting from the top.


        :param prompt: Context to give to the AI (raw text or list of tokens)
        :param model: Model to use for the AI
        :param preset: Preset to use for the generation settings
        :param global_settings: Global settings (used for generation)
        :param bad_words: Tokens to ban for this generation
        :param biases: Tokens to bias (up or down) for this generation
        :param prefix: Module to use for this generation (see :ref:`list of modules <list-of-modules>`)
        :param stop_sequences: List of strings or tokens to stop the generation at
        :param kwargs: Additional parameters to pass to the requests. Can also be used to overwrite existing parameters

        :return: Content that has been generated
        """

        async for e in self._generate(
            prompt,
            model,
            preset,
            global_settings,
            bad_words,
            biases,
            prefix,
            stop_sequences,
            True,
            **kwargs,
        ):
            yield json.loads(e)

    async def generate_image(
        self,
        prompt: str,
        model: ImageModel,
        preset: ImagePreset,
        action: ImageGenerationType = ImageGenerationType.NORMAL,
        **kwargs,
    ) -> AsyncIterable[Union[str, bytes]]:
        """
        Generate one or multiple image(s)

        :param prompt: Prompt to give to the AI (raw text describing the wanted image)
        :param model: Model to use for the AI
        :param preset: Preset to use for the generation settings
        :param action: Type of image generation to use
        :param kwargs: Additional parameters to pass to the requests. Can also be used to overwrite existing parameters

        :return: Pair(s) (name, image) that have been generated
        """

        settings = preset.to_settings(model)
        settings.update(kwargs)

        # TODO: allow to disable the removal of nsfw ? How to tackle this cleanly
        uc = settings["negative_prompt"]
        if "nsfw" in prompt and uc.startswith("nsfw,"):
            settings["negative_prompt"] = uc[len("nsfw,") :].strip()

        quality_toggle = settings["qualityToggle"]
        if quality_toggle:
            if model in (
                ImageModel.Anime_Full,
                ImageModel.Anime_Curated,
                ImageModel.Furry,
                ImageModel.Inpainting_Anime_Full,
                ImageModel.Inpainting_Anime_Curated,
                ImageModel.Inpainting_Furry,
            ):
                prompt = f"masterpiece, best quality, {prompt}"
            elif model is ImageModel.Anime_v2:
                prompt = f"very aesthetic, best quality, absurdres, {prompt}"
            elif model in (ImageModel.Anime_v3, ImageModel.Inpainting_Anime_v3):
                prompt = f"{prompt}, best quality, amazing quality, very aesthetic, absurdres"

        async for e in self._parent.low_level.generate_image(prompt, model, action, settings):
            yield e
