import copy
import enum
import io
import json
import operator
import zipfile
from typing import Any, AsyncIterator, Dict, List, NoReturn, Optional, Tuple, Union
from urllib.parse import quote, urlencode

from aiohttp import ClientSession
from aiohttp.client_reqrep import ClientResponse

from novelai_api.ImagePreset import ControlNetModel, ImageGenerationType, ImageModel
from novelai_api.NovelAIError import NovelAIError
from novelai_api.Preset import Model
from novelai_api.python_utils import NoneType, assert_len, assert_type
from novelai_api.SchemaValidator import SchemaValidator
from novelai_api.Tokenizer import Tokenizer
from novelai_api.utils import tokens_to_b64

# === INTERNALS === #
SSE_FIELDS = ["event", "data", "id", "retry"]


def print_with_parameters(args: Dict[str, Any]):
    """
    Print the provided parameters in a nice way
    """

    a = copy.deepcopy(args)
    if "input" in a:
        a["input"] = f"{a['input'][:10]}...{a['input'][-10:]}" if 30 < len(a["input"]) else a["input"]

    if "parameters" in a:
        a["parameters"] = {k: str(v) for k, v in a["parameters"].items()}

    print(json.dumps(a, indent=4))


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
    async def _parse_sse_stream(rsp: ClientResponse) -> AsyncIterator[Dict[str, str]]:
        """
        Parse a stream of Server Sent Event from an aiohttp ClientResponse
        Specs: https://html.spec.whatwg.org/multipage/server-sent-events.html

        This function consider all end of line to be '\\n'. '\\r' is not handled, albeit legal in the spec
        """

        sse_data = {"data": []}
        modified = False

        partial_data: str = ""
        async for chunk in rsp.content.iter_any():
            for line in f"{partial_data}{chunk.decode('utf-8')}".splitlines(True):
                if line in ("", "\n"):
                    # empty line = dispatch event if modified
                    if modified:
                        sse_data["data"] = "\n".join(sse_data["data"])
                        yield sse_data

                        sse_data = {"data": []}
                        modified = False

                    continue

                # no newline = partial line
                if not line.endswith("\n"):
                    partial_data = line
                    continue

                # strip the newline
                line = line[:-1]

                colon = line.find(":")

                # starting with colon = ignore the line
                if colon == 0:
                    continue

                # no colon = line is field, value is empty
                field = line if colon == -1 else line[:colon]
                value = "" if colon == -1 else line[colon + 1 :]

                if field not in SSE_FIELDS:
                    continue

                if value.startswith(" "):
                    value = value[1:]

                modified = True

                # multiple data fields = we merge them with a newline
                if field == "data":
                    sse_data["data"].append(value)
                else:
                    # ignore special handling of "retry" and NULL in "id"
                    sse_data[field] = value

    @classmethod
    async def _parse_response(cls, rsp: ClientResponse):
        """
        Parse the content of a ClientResponse depending on the content-type

        :param rsp: ClientResponse returned by a request
        """

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
                yield name, z.read(name)
            z.close()

        elif content_type == "text/event-stream":
            async for e in cls._parse_sse_stream(rsp):
                yield e["data"]

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
        """
        Change the access key of the given account

        :param current_key: Current key of the account
        :param new_key: New key of the account
        :param new_email: New email, if it changed
        """

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
        """
        Send the email for account verification

        :param email: Address to send the email to
        """

        assert_type(str, email=email)

        async for rsp, content in self.request("post", "/user/resend-email-verification", {"email": email}):
            return self._treat_response_bool(rsp, content, 200)

    async def verify_email(self, verification_token: str) -> bool:
        """
        Check the token sent for email verification

        :param verification_token: Token sent to the email address
        """

        assert_type(str, verification_token=verification_token)
        assert_len(64, verification_token=verification_token)

        async for rsp, content in self.request("post", "/user/verify-email", {"verificationToken": verification_token}):
            return self._treat_response_bool(rsp, content, 200)

    async def get_information(self) -> Dict[str, Any]:
        """
        Get extensive information about the account
        """

        async for rsp, content in self.request("get", "/user/information"):
            self._treat_response_object(rsp, content, 200)

            if self.is_schema_validation_enabled:
                SchemaValidator.validate("schema_AccountInformationResponse", content)

            return content

    async def request_account_recovery(self, email: str) -> bool:
        """
        Send a recovery token to the provided email address, if the account has been lost
        **WARNING**: the content will not be readable with a different encryption key

        :param email: Address to send the email to
        """

        assert_type(str, email=email)

        async for rsp, content in self.request("post", "/user/recovery/request", {"email": email}):
            return self._treat_response_bool(rsp, content, 202)

    async def recover_account(self, recovery_token: str, new_key: str, delete_content: bool = False) -> Dict[str, Any]:
        """
        Recover the lost account

        :param recovery_token: Token sent to the given email address
        :param new_key: New access key for the account
        :param delete_content: Delete all content that was on the account
        """

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
        """
        Delete the account
        """

        async for rsp, content in self.request("post", "/user/delete", None):
            return self._treat_response_bool(rsp, content, 200)

    async def get_data(self) -> Dict[str, Any]:
        """
        Get various data about the account
        """

        async for rsp, content in self.request("get", "/user/data"):
            self._treat_response_object(rsp, content, 200)

            if self.is_schema_validation_enabled:
                # FIXME: doesn't seem right
                SchemaValidator.validate("schema_AccountInformationResponse", content)

            return content

    async def get_priority(self) -> Dict[str, Any]:
        """
        Get the priority information of the account

        The priority system is a legacy system and isn't really important
        """

        async for rsp, content in self.request("get", "/user/priority"):
            self._treat_response_object(rsp, content, 200)

            if self.is_schema_validation_enabled:
                SchemaValidator.validate("schema_PriorityResponse", content)

            return content

    class SubscriptionTier(enum.IntEnum):
        """
        Index of the subscription tiers

        PAPER tier is the free trial
        """

        PAPER = 0
        TABLET = 1
        SCROLL = 2
        OPUS = 3

    async def get_subscription(self) -> Dict[str, Any]:
        """
        Get various information about the account's subscription
        """

        async for rsp, content in self.request("get", "/user/subscription"):
            self._treat_response_object(rsp, content, 200)

            if self.is_schema_validation_enabled:
                SchemaValidator.validate("schema_SubscriptionResponse", content)

            return content

    async def get_keystore(self) -> Dict[str, str]:
        """
        Get the keystore

        The keystore is the storage for the encryption keys of any content on the account.
        Losing it is equal to losing all your encrypted content
        """

        async for rsp, content in self.request("get", "/user/keystore"):
            self._treat_response_object(rsp, content, 200)

            if self.is_schema_validation_enabled:
                SchemaValidator.validate("schema_GetKeystoreResponse", content)

            return content

    async def set_keystore(self, keystore: Dict[str, str]) -> bool:
        """
        Set the keystore

        The keystore is the storage for the encryption keys of any content on the account.
        Losing it (or overwriting it with wrong data) is equal to losing all your encrypted content
        """

        assert_type(dict, keystore=keystore)

        async for rsp, content in self.request("put", "/user/keystore", keystore):
            return self._treat_response_object(rsp, content, 200)

    async def download_objects(self, object_type: str) -> Dict[str, List[Dict[str, Union[str, int]]]]:
        """
        Download all the objects of a given type from the account

        :param object_type: Type of the objects to download
        """

        assert_type(str, object_type=object_type)

        async for rsp, content in self.request("get", f"/user/objects/{object_type}"):
            self._treat_response_object(rsp, content, 200)

            if self.is_schema_validation_enabled:
                SchemaValidator.validate("schema_ObjectsResponse", content)

            return content

    async def upload_objects(self, object_type: str, meta: str, data: str) -> bool:
        """
        Upload multiple objects of the given type

        :param object_type: Type of the objects to upload
        :param meta: Meta of the objects to upload (meta links to encryption key in keystore)
        :param data: Serialized data of the content to upload
        """

        assert_type(str, object_type=object_type, meta=meta, data=data)
        assert_len(128, operator.le, meta=meta)

        async for rsp, content in self.request("put", f"/user/objects/{object_type}", {"meta": meta, "data": data}):
            self._treat_response_object(rsp, content, 200)

            return content

    async def download_object(self, object_type: str, object_id: str) -> Dict[str, Union[str, int]]:
        """
        Download the selected object of a given type from the account

        :param object_type: Type of the object to download
        :param object_id: Id of the selected object
        """

        assert_type(str, object_type=object_type, object_id=object_id)

        async for rsp, content in self.request("get", f"/user/objects/{object_type}/{object_id}"):
            self._treat_response_object(rsp, content, 200)

            if self.is_schema_validation_enabled:
                SchemaValidator.validate("schema_userData", content)

            return content

    async def upload_object(self, object_type: str, object_id: str, meta: str, data: str) -> bool:
        """
        Upload an object of then given type

        :param object_type: Type of the object to upload
        :param meta: Meta of the object to upload (meta links to encryption key in keystore)
        :param data: Serialized data of the content to upload
        :param object_id: Id of the selected object
        """

        assert_type(str, object_type=object_type, object_id=object_id, meta=meta, data=data)
        assert_len(128, operator.le, meta=meta)

        params = {"meta": meta, "data": data}
        async for rsp, content in self.request("patch", f"/user/objects/{object_type}/{object_id}", params):
            self._treat_response_object(rsp, content, 200)

            return content

    async def delete_object(self, object_type: str, object_id: str) -> Dict[str, Union[str, int]]:
        """
        Download the selected object of a given type from the account

        :param object_type: Type of the object to delete
        :param object_id: Id of the selected object
        """

        assert_type(str, object_type=object_type, object_id=object_id)

        async for rsp, content in self.request("delete", f"/user/objects/{object_type}/{object_id}"):
            return self._treat_response_object(rsp, content, 200)

    async def get_settings(self) -> str:
        """
        Get the account settings. The format is arbitrary.
        """

        async for rsp, content in self.request("get", "/user/clientsettings"):
            return self._treat_response_object(rsp, content, 200)

    async def set_settings(self, value: str) -> bool:
        """
        Set the account settings. The format is arbitrary.
        """

        assert_type(str, value=value)

        async for rsp, content in self.request("put", "/user/clientsettings", value):
            return self._treat_response_bool(rsp, content, 200)

    async def bind_subscription(self, payment_processor: str, subscription_id: str) -> bool:
        """
        Bind payment information to the account to renew subscription monthly
        """

        assert_type(str, payment_processor=payment_processor, subscription_id=subscription_id)

        data = {"paymentProcessor": payment_processor, "subscriptionId": subscription_id}

        async for rsp, content in self.request("post", "/user/subscription/bind", data):
            return self._treat_response_bool(rsp, content, 201)

    async def change_subscription(self, new_plan: str) -> bool:
        """
        Change the subscription tier. Payment information should still be bound to the account
        """

        assert_type(str, new_plan=new_plan)

        async for rsp, content in self.request("post", "/user/subscription/change", {"newSubscriptionPlan": new_plan}):
            return self._treat_response_bool(rsp, content, 200)

    async def generate(self, prompt: Union[List[int], str], model: Model, params: Dict[str, Any], stream: bool = False):
        """
        Generate text with streaming support

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
        """
        Not implemented
        """

        raise NotImplementedError("Function is not implemented yet")

    async def train_module(self, data: str, rate: int, steps: int, name: str, desc: str) -> Dict[str, Any]:
        """
        Train a module for text gen

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
        Get the modules currently in training or that finished training
        """

        async for rsp, content in self.request("get", "/ai/module/all"):
            self._treat_response_object(rsp, content, 200)

            if self.is_schema_validation_enabled:
                SchemaValidator.validate("schema_AiModuleDtos", content)

            return content

    async def get_trained_module(self, module_id: str) -> Dict[str, Any]:
        """
        Get a module currently in training or that finished training

        :param module_id: Id of the selected module
        """

        assert_type(str, module_id=module_id)

        async for rsp, content in self.request("get", f"/ai/module/{module_id}"):
            self._treat_response_object(rsp, content, 200)

            if self.is_schema_validation_enabled:
                SchemaValidator.validate("schema_AiModuleDto", content)

            return content

    async def delete_module(self, module_id: str) -> Dict[str, Any]:
        """
        Delete a module currently in training or that finished training

        :param module_id: Id of the selected module

        :return: Module that got deleted
        """

        assert_type(str, module_id=module_id)

        async for rsp, content in self.request("delete", f"/ai/module/{module_id}"):
            self._treat_response_object(rsp, content, 200)

            # TODO: verify response ?

            return content

    async def generate_voice(self, text: str, seed: str, voice: int, opus: bool, version: str) -> Dict[str, Any]:
        """
        Generate the Text To Speech of the given text

        :param text: Text to synthesize into voice (text will be cut to 1000 characters backend-side)
        :param seed: Voice to use
        :param voice: Index of the voice to use
        :param opus: True for WebM format, False for mp3 format
        :param version: Version of the TTS ("v1" or "v2")

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
                "model": model.value,
                "prompt": tag,
            },
            quote_via=quote,
        )

        async for rsp, content in self.request("get", f"/ai/generate-image/suggest-tags?{query}"):
            self._treat_response_object(rsp, content, 200)

            return content

    async def generate_image(
        self, prompt: str, model: ImageModel, action: ImageGenerationType, parameters: Dict[str, Any]
    ) -> AsyncIterator[Tuple[str, bytes]]:
        """
        Generate one or multiple image(s)

        :param prompt: Prompt for the image
        :param model: Model to generate the image
        :param action: Type of image generation to use
        :param parameters: Parameters for the images

        :return: (name, data) pairs for the raw PNG image(s)
        """

        assert_type(str, prompt=prompt)
        assert_type(ImageModel, model=model)
        assert_type(dict, parameters=parameters)

        args = {
            "input": prompt,
            "model": model.value,
            "action": action.value,
            "parameters": parameters,
        }

        async for rsp, content in self.request("post", "/ai/generate-image", args):
            self._treat_response_object(rsp, content, 200)

            yield content

    async def generate_controlnet_mask(self, model: ControlNetModel, image: str) -> Tuple[str, bytes]:
        """
        Get the ControlNet's mask for the given image. Used for ImageSampler.controlnet_condition

        :param model: ControlNet model to use
        :param image: b64 encoded PNG image to get the mask of

        :return: A pair (name, data) for the raw PNG image
        """

        assert_type(ControlNetModel, model=model)
        assert_type(str, image=image)

        args = {"model": model.value, "parameters": {"image": image}}

        async for rsp, content in self.request("post", "/ai/annotate-image", args):
            self._treat_response_object(rsp, content, 200)

            return content

    async def upscale_image(self, image: str, width: int, height: int, scale: int) -> Tuple[str, bytes]:
        """
        Upscale the given image. Afaik, the only allowed values for scale are 2 and 4.

        :param image: b64 encoded PNG image to upscale
        :param width: Width of the starting image
        :param height: Height of the starting image
        :param scale: Upscaling factor (final width = starting width * scale, final height = starting height * scale)

        :return: A pair (name, data) for the raw PNG image
        """

        assert_type(str, image=image)
        assert_type(int, width=width, height=height, scale=scale)

        args = {"image": image, "width": width, "height": height, "scale": scale}

        async for rsp, content in self.request("post", "/ai/upscale", args):
            self._treat_response_object(rsp, content, 200)

            return content
