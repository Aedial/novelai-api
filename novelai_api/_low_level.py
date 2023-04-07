import enum
import io
import json
import operator
import zipfile
from typing import Any, AsyncIterator, Dict, List, NoReturn, Optional, Union
from urllib.parse import quote, urlencode

from aiohttp import ClientSession
from aiohttp.client_reqrep import ClientResponse

from novelai_api.ImagePreset import ControlNetModel, ImageModel
from novelai_api.NovelAIError import NovelAIError
from novelai_api.Preset import Model
from novelai_api.SchemaValidator import SchemaValidator
from novelai_api.Tokenizer import Tokenizer
from novelai_api.utils import NoneType, assert_len, assert_type, tokens_to_b64


# === INTERNALS === #
# === API === #
class LowLevel:
    _parent: "NovelAIAPI"  # noqa: F821
    _is_async: bool

    is_schema_validation_enabled: bool

    def __init__(self, parent: "NovelAIAPI"):  # noqa: F821
        self._parent = parent
        self.is_schema_validation_enabled = True

    @staticmethod
    def _treat_response_object(rsp: ClientResponse, content: Any, status: int) -> Any:
        # error is an unexpected fail and usually come with a success status
        if isinstance(content, dict) and "error" in content:
            raise NovelAIError(rsp.status, content["error"])

        # success
        if rsp.status == status:
            return content

        # not success, but valid response
        if isinstance(content, dict) and "message" in content:  # NovelAI REST API error
            raise NovelAIError(rsp.status, content["message"])

        # HTTPException error
        if hasattr(rsp, "reason"):
            raise NovelAIError(rsp.status, str(rsp.reason))

        raise NovelAIError(rsp.status, "Unknown error")

    def _treat_response_bool(self, rsp: ClientResponse, content: Any, status: int) -> bool:
        if rsp.status == status:
            return True

        self._treat_response_object(rsp, content, status)
        return False

    @staticmethod
    async def _parse_event_stream(rsp: ClientResponse):
        content = b""

        async for chunk in rsp.content.iter_any():
            # the event can be in the middle of a chunk... tfw...
            if content and b"event" in chunk:
                event_pos = chunk.find(b"event:")
                content += chunk[:event_pos]

                stream_data = {}
                for line in content.decode().strip("\n").splitlines():
                    if line == "":
                        continue

                    colon = line.find(":")
                    # TODO: replace by a meaningful error
                    if colon == -1:
                        raise NovelAIError(-1, f"Malformed data stream line: '{line}'")

                    stream_data[line[:colon].strip()] = line[colon + 1 :].strip()

                # TODO: replace by a meaningful error
                assert "data" in stream_data
                data = stream_data["data"]

                if data.startswith("{") and data.endswith("}"):
                    data = json.loads(data)

                yield data

                content = chunk[event_pos:]
            else:
                # TODO: Is there no way to check for malformed chunks here ? Massively sucks.
                #       .iter_chunks() doesn't help either, as the request doesn't fit in an HTTP chunk
                content += chunk

    @classmethod
    async def _parse_response(cls, rsp: ClientResponse):
        content_type = rsp.content_type

        if content_type == "application/json":
            yield await rsp.json()

        elif content_type in ("text/plain", "text/html"):
            yield await rsp.text()

        elif content_type in ("audio/mpeg", "audio/webm"):
            yield await rsp.read()

        elif content_type == "application/x-zip-compressed":
            z = zipfile.ZipFile(io.BytesIO(await rsp.read()))
            for name in z.namelist():
                yield z.read(name)
            z.close()

        elif content_type == "text/event-stream":
            async for e in cls._parse_event_stream(rsp):
                yield e

        else:
            raise NovelAIError(-1, f"Unsupported type: {rsp.content_type}")

    async def request(self, method: str, endpoint: str, data: Optional[Union[Dict[str, Any], str]] = None):
        """
        Send request with support for data streaming

        :param method: Method of the request (get, post, delete)
        :param endpoint: Endpoint of the request
        :param data: Data to pass to the method if needed
        """

        url = f"{self._parent.BASE_ADDRESS}{endpoint}"

        is_sync = self._parent.session is None
        session = ClientSession() if is_sync else self._parent.session

        kwargs = {
            "timeout": self._parent.timeout,
            "cookies": self._parent.cookies,
            "headers": self._parent.headers,
            "json" if isinstance(data, dict) else "data": data,
        }

        if self._parent.proxy is not None:
            kwargs["proxy"] = self._parent.proxy

        if self._parent.proxy_auth is not None:
            kwargs["proxy_auth"] = self._parent.proxy_auth

        try:
            async with session.request(method, url, **kwargs) as rsp:
                async for e in self._parse_response(rsp):
                    yield rsp, e
        except Exception as e:
            raise e
        finally:
            if is_sync:
                await session.close()

    async def is_reachable(self) -> bool:
        """
        Check if the NovelAI API is reachable

        :return: True if reachable, False if not
        """

        async for rsp, content in self.request("get", "/"):
            return self._treat_response_bool(rsp, content, 200)

    async def register(
        self, recapcha: str, access_key: str, email: Optional[str], giftkey: Optional[str] = None
    ) -> bool:
        """
        Register a new account

        :param recapcha: Recapcha of the NovelAI website
        :param access_key: Access key of the account
        :param email: Hashed email (used for recovery)
        :param giftkey: Giftkey

        :return: True if success
        """

        assert_type(str, recapcha=recapcha, access_key=access_key)
        assert_type((str, NoneType), email=email, giftkey=giftkey)
        assert_len(64, access_key=access_key)
        assert_len(64, email=email)

        data = {"recapcha": recapcha, "key": access_key}

        if email is not None:
            data["email"] = email
        if giftkey is not None:
            data["giftkey"] = giftkey

        async for rsp, content in self.request("post", "/user/register", data):
            self._treat_response_object(rsp, content, 201)

            if self.is_schema_validation_enabled:
                SchemaValidator.validate("schema_SuccessfulLoginResponse", content)

            return content

    async def login(self, access_key: str) -> Dict[str, str]:
        """
        Log in to the account

        :param access_key: Access key of the account

        :return: Response of the request
        """

        assert_type(str, access_key=access_key)
        assert_len(64, access_key=access_key)

        async for rsp, content in self.request("post", "/user/login", {"key": access_key}):
            self._treat_response_object(rsp, content, 201)

            if self.is_schema_validation_enabled:
                SchemaValidator.validate("schema_SuccessfulLoginResponse", content)

            return content

    async def change_access_key(
        self, current_key: str, new_key: str, new_email: Optional[str] = None
    ) -> Dict[str, str]:
        assert_type(str, current_key=current_key, new_key=new_key)
        assert_type((str, NoneType), new_email=new_email)
        assert_len(64, current_key=current_key, new_key=new_key)

        data = {"currentAccessKey": current_key, "newAccessKey": new_key}

        if new_email is not None:
            data["newEmail"] = new_email

        async for rsp, content in self.request("post", "/user/change-access-key", data):
            self._treat_response_object(rsp, content, 200)

            if self.is_schema_validation_enabled:
                SchemaValidator.validate("schema_SuccessfulLoginResponse", content)

            return content

    async def send_email_verification(self, email: str) -> bool:
        assert_type(str, email=email)

        async for rsp, content in self.request("post", "/user/resend-email-verification", {"email": email}):
            return self._treat_response_bool(rsp, content, 200)

    async def verify_email(self, verification_token: str) -> bool:
        assert_type(str, verification_token=verification_token)
        assert_len(64, verification_token=verification_token)

        async for rsp, content in self.request("post", "/user/verify-email", {"verificationToken": verification_token}):
            return self._treat_response_bool(rsp, content, 200)

    async def get_information(self) -> Dict[str, Any]:
        async for rsp, content in self.request("get", "/user/information"):
            self._treat_response_object(rsp, content, 200)

            if self.is_schema_validation_enabled:
                SchemaValidator.validate("schema_AccountInformationResponse", content)

            return content

    async def request_account_recovery(self, email: str) -> bool:
        assert_type(str, email=email)

        async for rsp, content in self.request("post", "/user/recovery/request", {"email": email}):
            return self._treat_response_bool(rsp, content, 202)

    async def recover_account(self, recovery_token: str, new_key: str, delete_content: bool = False) -> Dict[str, Any]:
        assert_type(str, recovery_token=recovery_token, new_key=new_key)
        assert_type(bool, delete_content=delete_content)
        assert_len(16, operator.ge, recovery_token=recovery_token)
        assert_len(64, new_key=new_key)

        data = {
            "recoveryToken": recovery_token,
            "newAccessKey": new_key,
            "deleteContent": delete_content,
        }

        async for rsp, content in self.request("post", "/user/recovery/recover", data):
            self._treat_response_object(rsp, content, 201)

            if self.is_schema_validation_enabled:
                SchemaValidator.validate("schema_SuccessfulLoginResponse", content)

            return content

    async def delete_account(self) -> bool:
        async for rsp, content in self.request("post", "/user/delete", None):
            return self._treat_response_bool(rsp, content, 200)

    async def get_data(self) -> Dict[str, Any]:
        async for rsp, content in self.request("get", "/user/data"):
            self._treat_response_object(rsp, content, 200)

            if self.is_schema_validation_enabled:
                SchemaValidator.validate("schema_AccountInformationResponse", content)

            return content

    async def get_priority(self) -> Dict[str, Any]:
        async for rsp, content in self.request("get", "/user/priority"):
            self._treat_response_object(rsp, content, 200)

            if self.is_schema_validation_enabled:
                SchemaValidator.validate("schema_PriorityResponse", content)

            return content

    class SubscriptionTier(enum.IntEnum):
        PAPER = 0
        TABLET = 1
        SCROLL = 2
        OPUS = 3

    async def get_subscription(self) -> Dict[str, Any]:
        async for rsp, content in self.request("get", "/user/subscription"):
            self._treat_response_object(rsp, content, 200)

            if self.is_schema_validation_enabled:
                SchemaValidator.validate("schema_SubscriptionResponse", content)

            return content

    async def get_keystore(self) -> Dict[str, str]:
        async for rsp, content in self.request("get", "/user/keystore"):
            self._treat_response_object(rsp, content, 200)

            if self.is_schema_validation_enabled:
                SchemaValidator.validate("schema_GetKeystoreResponse", content)

            return content

    async def set_keystore(self, keystore: Dict[str, str]) -> bool:
        assert_type(dict, keystore=keystore)

        async for rsp, content in self.request("put", "/user/keystore", keystore):
            return self._treat_response_object(rsp, content, 200)

    async def download_objects(self, object_type: str) -> Dict[str, List[Dict[str, Union[str, int]]]]:
        assert_type(str, object_type=object_type)

        async for rsp, content in self.request("get", f"/user/objects/{object_type}"):
            self._treat_response_object(rsp, content, 200)

            if self.is_schema_validation_enabled:
                SchemaValidator.validate("schema_ObjectsResponse", content)

            return content

    async def upload_objects(self, object_type: str, meta: str, data: str) -> bool:
        assert_type(str, object_type=object_type, meta=meta, data=data)
        assert_len(128, operator.le, meta=meta)

        async for rsp, content in self.request("put", f"/user/objects/{object_type}", {"meta": meta, "data": data}):
            self._treat_response_object(rsp, content, 200)

            return content

    async def download_object(self, object_type: str, object_id: str) -> Dict[str, Union[str, int]]:
        assert_type(str, object_type=object_type, object_id=object_id)

        async for rsp, content in self.request("get", f"/user/objects/{object_type}/{object_id}"):
            self._treat_response_object(rsp, content, 200)

            if self.is_schema_validation_enabled:
                SchemaValidator.validate("schema_userData", content)

            return content

    async def upload_object(self, object_type: str, object_id: str, meta: str, data: str) -> bool:
        assert_type(str, object_type=object_type, object_id=object_id, meta=meta, data=data)
        assert_len(128, operator.le, meta=meta)

        params = {"meta": meta, "data": data}
        async for rsp, content in self.request("patch", f"/user/objects/{object_type}/{object_id}", params):
            self._treat_response_object(rsp, content, 200)

            return content

    async def delete_object(self, object_type: str, object_id: str) -> Dict[str, Union[str, int]]:
        assert_type(str, object_type=object_type, object_id=object_id)

        async for rsp, content in self.request("delete", f"/user/objects/{object_type}/{object_id}"):
            return self._treat_response_object(rsp, content, 200)

    async def get_settings(self) -> str:
        async for rsp, content in self.request("get", "/user/clientsettings"):
            return self._treat_response_object(rsp, content, 200)

    async def set_settings(self, value: str) -> bool:
        assert_type(str, value=value)

        async for rsp, content in self.request("put", "/user/clientsettings", value):
            return self._treat_response_bool(rsp, content, 200)

    async def bind_subscription(self, payment_processor: str, subscription_id: str) -> bool:
        assert_type(str, payment_processor=payment_processor, subscription_id=subscription_id)

        data = {"paymentProcessor": payment_processor, "subscriptionId": subscription_id}

        async for rsp, content in self.request("post", "/user/subscription/bind", data):
            return self._treat_response_bool(rsp, content, 201)

    async def change_subscription(self, new_plan: str) -> bool:
        assert_type(str, new_plan=new_plan)

        async for rsp, content in self.request("post", "/user/subscription/change", {"newSubscriptionPlan": new_plan}):
            return self._treat_response_bool(rsp, content, 200)

    async def generate(self, prompt: Union[List[int], str], model: Model, params: Dict[str, Any], stream: bool = False):
        """
        :param prompt: Input to be sent the AI
        :param model: Model of the AI
        :param params: Generation parameters
        :param stream: Use data streaming for the response

        :return: Generated output
        """

        assert_type((str, list), prompt=prompt)
        assert_type(Model, model=model)
        assert_type(dict, params=params)
        assert_type(bool, stream=stream)

        if isinstance(prompt, str):
            prompt = Tokenizer.encode(model, prompt)

        prompt = tokens_to_b64(prompt)
        args = {"input": prompt, "model": model.value, "parameters": params}

        endpoint = "/ai/generate-stream" if stream else "/ai/generate"

        async for rsp, content in self.request("post", endpoint, args):
            self._treat_response_object(rsp, content, 201)

            yield content

    async def classify(self) -> NoReturn:
        raise NotImplementedError("Function is not implemented yet")

    async def train_module(self, data: str, rate: int, steps: int, name: str, desc: str) -> Dict[str, Any]:
        """
        :param data: Dataset of the module, in one single string
        :param rate: Learning rate of the training
        :param steps: Number of steps to train the module for
        :param name: Name of the module
        :param desc: Description of the module

        :return: Status of the module being trained
        """

        assert_type(str, data=data, name=name, desc=desc)
        assert_type(int, rate=rate, steps=steps)

        params = {
            "data": data,
            "lr": rate,
            "steps": steps,
            "name": name,
            "description": desc,
        }

        async for rsp, content in self.request("post", "/ai/module/train", params):
            self._treat_response_object(rsp, content, 201)

            # TODO: verify response ?

            return content

    async def get_trained_modules(self) -> List[Dict[str, Any]]:
        """
        :return: List of modules trained or in training
        """

        async for rsp, content in self.request("get", "/ai/module/all"):
            self._treat_response_object(rsp, content, 200)

            if self.is_schema_validation_enabled:
                SchemaValidator.validate("schema_AiModuleDtos", content)

            return content

    async def get_trained_module(self, module_id: str) -> Dict[str, Any]:
        """
        :param module_id: Id of the module

        :return: Selected module, trained or in training
        """

        assert_type(str, module_id=module_id)

        async for rsp, content in self.request("get", f"/ai/module/{module_id}"):
            self._treat_response_object(rsp, content, 200)

            if self.is_schema_validation_enabled:
                SchemaValidator.validate("schema_AiModuleDto", content)

            return content

    async def delete_module(self, module_id: str) -> Dict[str, Any]:
        """
        Delete the module with id :ref: `module_id`

        :param module_id: Id of the module

        :return: Module that got deleted
        """

        assert_type(str, module_id=module_id)

        async for rsp, content in self.request("delete", f"/ai/module/{module_id}"):
            self._treat_response_object(rsp, content, 200)

            # TODO: verify response ?

            return content

    async def generate_voice(self, text: str, seed: str, voice: int, opus: bool, version: str) -> Dict[str, Any]:
        """
        Generate the Text-to-Speech of :ref: `text` using the given seed and voice

        :param text: Text to synthetize into voice
        :param seed: Person to use the voice of
        :param voice: Index of the voice to use
        :param opus: True for WebM format, False for mp3 format
        :param version: Version of the TTS

        :return: TTS audio data of the text
        """

        assert_type(str, text=text, seed=seed, version=version)
        assert_type(int, voice=voice)
        assert_type(bool, opus=opus)

        # urlencode keeps capitalization on bool =_=
        opus = "true" if opus else "false"
        query = urlencode(
            {
                "text": text,
                "seed": seed,
                "voice": voice,
                "opus": opus,
                "version": version,
            },
            quote_via=quote,
        )

        async for rsp, content in self.request("get", f"/ai/generate-voice?{query}"):
            self._treat_response_object(rsp, content, 200)

            return content

    async def suggest_tags(self, tag: str, model: ImageModel) -> Dict[str, Any]:
        """
        Suggest tags with a certain confidence, considering how much the tag is used in the dataset

        :param tag: Tag to suggest others of
        :param model: Image model to get the tags from

        :return: List of similar tags with a confidence level
        """

        assert_type(str, tag=tag)
        assert_type(ImageModel, model=model)

        query = urlencode(
            {
                "model": model,
                "prompt": tag,
            },
            quote_via=quote,
        )

        async for rsp, content in self.request("get", f"/ai/generate-image/suggest-tags?{query}"):
            self._treat_response_object(rsp, content, 200)

            return content

    async def generate_image(self, prompt: str, model: ImageModel, parameters: Dict[str, Any]) -> AsyncIterator[bytes]:
        """
        Generate one or multiple images

        :param prompt: Prompt for the image
        :param model: Model to generate the image
        :param parameters: Parameters for the images

        :return: Raw PNG image(s)
        """

        assert_type(str, prompt=prompt)
        assert_type(ImageModel, model=model)
        assert_type(dict, parameters=parameters)

        args = {
            "input": prompt,
            "model": model.value,
            "parameters": parameters,
        }

        async for rsp, content in self.request("post", "/ai/generate-image", args):
            self._treat_response_object(rsp, content, 200)

            yield content

    async def generate_controlnet_mask(self, model: ControlNetModel, image: str) -> bytes:
        """
        Get the ControlNet's mask for the image. Used for ImageSampler["controlnet_condition"]

        :param model: ControlNet model to use
        :param image: b64 encoded PNG image to get the mask of

        :return: A raw PNG image
        """

        assert_type(ControlNetModel, model=model)
        assert_type(str, image=image)

        args = {"model": model.value, "parameters": {"image": image}}

        async for rsp, content in self.request("post", "/ai/annotate-image", args):
            self._treat_response_object(rsp, content, 200)

            return content

    async def upscale_image(self, image: str, width: int, height: int, scale: int) -> bytes:
        """
        Upscale the image. Afaik, the only allowed values for scale are 2 and 4.

        :param image: b64 encoded PNG image to upscale
        :param width: Width of the starting image
        :param height: Height of the starting image
        :param scale: Upscaling factor (final width = starting width * scale, final height = starting height * scale)

        :return: A raw PNG image
        """

        assert_type(str, image=image)
        assert_type(int, width=width, height=height, scale=scale)

        args = {"image": image, "width": width, "height": height, "scale": scale}

        async for rsp, content in self.request("post", "/ai/upscale", args):
            self._treat_response_object(rsp, content, 200)

            return content
