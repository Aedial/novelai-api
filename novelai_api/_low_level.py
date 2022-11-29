import enum
import json
import operator
from typing import Any, AsyncIterable, Dict, List, NoReturn, Optional, Tuple, Union
from urllib.parse import quote, urlencode

from aiohttp import ClientSession
from aiohttp.client_reqrep import ClientResponse

from novelai_api.ImagePreset import ImageModel
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
    async def _treat_response(rsp: ClientResponse, data: Any) -> Any:
        if rsp.content_type == "application/json":
            return await data.json()

        if rsp.content_type in ("text/plain", "text/html"):
            return await data.text()

        if rsp.content_type in ("audio/mpeg", "audio/webm"):
            return await data.read()

        raise RuntimeError(f"Unsupported type: {rsp.content_type}")

    @staticmethod
    def _parse_stream_data(stream_content: str) -> Dict[str, Any]:
        stream_data = {}

        for line in stream_content.strip("\n").splitlines():
            if line == "":
                continue

            colon = line.find(":")
            # TODO: replace by a meaningful error
            if colon == -1:
                raise NovelAIError(0, f"Malformed data stream line: '{line}'")

            stream_data[line[:colon]] = line[colon + 1 :].strip()

        return stream_data

    async def _treat_response_stream(self, rsp: ClientResponse, data: bytes) -> Any:
        data = data.decode()

        if rsp.content_type == "text/event-stream":
            stream_data = self._parse_stream_data(data)

            # TODO: replace by a meaningful error
            assert "data" in stream_data
            data = stream_data["data"]

            if data.startswith("{") and data.endswith("}"):
                data = json.loads(data)

        return data

    async def _request(
        self, method: str, url: str, session: ClientSession, data: Union[Dict[str, Any], str], stream: bool
    ):

        kwargs = {
            "timeout": self._parent._timeout,  # noqa
            "cookies": self._parent.cookies,
            "headers": self._parent.headers,
            "json" if isinstance(data, dict) else "data": data,
        }

        if self._parent.proxy is not None:
            kwargs["proxy"] = self._parent.proxy

        if self._parent.proxy_auth is not None:
            kwargs["proxy_auth"] = self._parent.proxy_auth

        async with session.request(method, url, **kwargs) as rsp:
            if stream:
                content = b""

                async for chunk in rsp.content.iter_any():
                    # the event can be in the middle of a chunk... tfw...
                    if content and b"event" in chunk:
                        event_pos = chunk.find(b"event:")
                        content += chunk[:event_pos]

                        yield rsp, await self._treat_response_stream(rsp, content)
                        content = chunk[event_pos:]
                    else:
                        # TODO: Is there no way to check for malformed chunks here ? Massively sucks.
                        #       .iter_chunks() doesn't help either, as the request doesn't fit in an HTTP chunk
                        content += chunk

                yield rsp, await self._treat_response_stream(rsp, content)
            else:
                yield rsp, await self._treat_response(rsp, rsp)

    async def request_stream(
        self, method: str, endpoint: str, data: Optional[Union[Dict[str, Any], str]] = None, stream: bool = True
    ):
        """
        Send request with support for data streaming

        :param method: Method of the request (get, post, delete)
        :param endpoint: Endpoint of the request
        :param data: Data to pass to the method if needed
        :param stream: Use data streaming for the response
        """

        url = f"{self._parent.BASE_ADDRESS}{endpoint}"

        is_sync = self._parent._session is None  # noqa
        session = ClientSession() if is_sync else self._parent._session  # noqa

        try:
            async for i in self._request(method, url, session, data, stream):
                yield i
        except Exception as e:
            raise e
        finally:
            if is_sync:
                await session.close()

    async def request(
        self, method: str, endpoint: str, data: Optional[Union[Dict[str, Any], str]] = None
    ) -> Tuple[ClientResponse, Any]:
        """
        Send request

        :param method: Method of the request (get, post, delete)
        :param endpoint: Endpoint of the request
        :param data: Data to pass to the method if needed
        """

        async for i in self.request_stream(method, endpoint, data, False):
            return i

    async def is_reachable(self) -> bool:
        """
        Check if the NovelAI API is reachable

        :return: True if reachable, False if not
        """

        rsp, content = await self.request("get", "/")
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

        rsp, content = await self.request("post", "/user/register", data)
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

        rsp, content = await self.request("post", "/user/login", {"key": access_key})
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

        rsp, content = await self.request("post", "/user/change-access-key", data)
        self._treat_response_object(rsp, content, 200)

        if self.is_schema_validation_enabled:
            SchemaValidator.validate("schema_SuccessfulLoginResponse", content)

        return content

    async def send_email_verification(self, email: str) -> bool:
        assert_type(str, email=email)

        rsp, content = await self.request("post", "/user/resend-email-verification", {"email": email})
        return self._treat_response_bool(rsp, content, 200)

    async def verify_email(self, verification_token: str) -> bool:
        assert_type(str, verification_token=verification_token)
        assert_len(64, verification_token=verification_token)

        rsp, content = await self.request("post", "/user/verify-email", {"verificationToken": verification_token})
        return self._treat_response_bool(rsp, content, 200)

    async def get_information(self) -> Dict[str, Any]:
        rsp, content = await self.request("get", "/user/information")
        self._treat_response_object(rsp, content, 200)

        if self.is_schema_validation_enabled:
            SchemaValidator.validate("schema_AccountInformationResponse", content)

        return content

    async def request_account_recovery(self, email: str) -> bool:
        assert_type(str, email=email)

        rsp, content = await self.request("post", "/user/recovery/request", {"email": email})
        return self._treat_response_bool(rsp, content, 202)

    async def recover_account(self, recovery_token: str, new_key: str, delete_content: bool = False) -> Dict[str, Any]:
        assert_type(str, recovery_token=recovery_token, new_key=new_key)
        assert_type(bool, delete_content=delete_content)
        assert_len(16, operator.ge, recovery_token=recovery_token)
        assert_len(64, new_key=new_key)

        rsp, content = await self.request(
            "post",
            "/user/recovery/recover",
            {
                "recoveryToken": recovery_token,
                "newAccessKey": new_key,
                "deleteContent": delete_content,
            },
        )
        self._treat_response_object(rsp, content, 201)

        if self.is_schema_validation_enabled:
            SchemaValidator.validate("schema_SuccessfulLoginResponse", content)

        return content

    async def delete_account(self) -> bool:
        rsp, content = await self.request("post", "/user/delete", None)
        return self._treat_response_bool(rsp, content, 200)

    async def get_data(self) -> Dict[str, Any]:
        rsp, content = await self.request("get", "/user/data")
        self._treat_response_object(rsp, content, 200)

        if self.is_schema_validation_enabled:
            SchemaValidator.validate("schema_AccountInformationResponse", content)

        return content

    async def get_priority(self) -> Dict[str, Any]:
        rsp, content = await self.request("get", "/user/priority")
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
        rsp, content = await self.request("get", "/user/subscription")
        self._treat_response_object(rsp, content, 200)

        if self.is_schema_validation_enabled:
            SchemaValidator.validate("schema_SubscriptionResponse", content)

        return content

    async def get_keystore(self) -> Dict[str, str]:
        rsp, content = await self.request("get", "/user/keystore")
        self._treat_response_object(rsp, content, 200)

        if self.is_schema_validation_enabled:
            SchemaValidator.validate("schema_GetKeystoreResponse", content)

        return content

    async def set_keystore(self, keystore: Dict[str, str]) -> bool:
        assert_type(dict, keystore=keystore)

        rsp, content = await self.request("put", "/user/keystore", keystore)
        return self._treat_response_object(rsp, content, 200)

    async def download_objects(self, object_type: str) -> Dict[str, List[Dict[str, Union[str, int]]]]:
        assert_type(str, object_type=object_type)

        rsp, content = await self.request("get", f"/user/objects/{object_type}")
        self._treat_response_object(rsp, content, 200)

        if self.is_schema_validation_enabled:
            SchemaValidator.validate("schema_ObjectsResponse", content)

        return content

    async def upload_objects(self, object_type: str, meta: str, data: str) -> bool:
        assert_type(str, object_type=object_type, meta=meta, data=data)
        assert_len(128, operator.le, meta=meta)

        rsp, content = await self.request("put", f"/user/objects/{object_type}", {"meta": meta, "data": data})
        self._treat_response_object(rsp, content, 200)

        return content

    async def download_object(self, object_type: str, object_id: str) -> Dict[str, Union[str, int]]:
        assert_type(str, object_type=object_type, object_id=object_id)

        rsp, content = await self.request("get", f"/user/objects/{object_type}/{object_id}")
        self._treat_response_object(rsp, content, 200)

        if self.is_schema_validation_enabled:
            SchemaValidator.validate("schema_userData", content)

        return content

    async def upload_object(self, object_type: str, object_id: str, meta: str, data: str) -> bool:
        assert_type(str, object_type=object_type, object_id=object_id, meta=meta, data=data)
        assert_len(128, operator.le, meta=meta)

        rsp, content = await self.request(
            "patch",
            f"/user/objects/{object_type}/{object_id}",
            {"meta": meta, "data": data},
        )
        self._treat_response_object(rsp, content, 200)

        return content

    async def delete_object(self, object_type: str, object_id: str) -> Dict[str, Union[str, int]]:
        assert_type(str, object_type=object_type, object_id=object_id)

        rsp, content = await self.request("delete", f"/user/objects/{object_type}/{object_id}")
        return self._treat_response_object(rsp, content, 200)

    async def get_settings(self) -> str:
        rsp, content = await self.request("get", "/user/clientsettings")
        return self._treat_response_object(rsp, content, 200)

    async def set_settings(self, value: str) -> bool:
        assert_type(str, value=value)

        rsp, content = await self.request("put", "/user/clientsettings", value)
        return self._treat_response_bool(rsp, content, 200)

    async def bind_subscription(self, payment_processor: str, subscription_id: str) -> bool:
        assert_type(str, payment_processor=payment_processor, subscription_id=subscription_id)

        rsp, content = await self.request(
            "post",
            "/user/subscription/bind",
            {"paymentProcessor": payment_processor, "subscriptionId": subscription_id},
        )
        return self._treat_response_bool(rsp, content, 201)

    async def change_subscription(self, new_plan: str) -> bool:
        assert_type(str, new_plan=new_plan)

        rsp, content = await self.request("post", "/user/subscription/change", {"newSubscriptionPlan": new_plan})
        return self._treat_response_bool(rsp, content, 200)

    async def generate(
        self,
        prompt: Union[List[int], str],
        model: Model,
        params: Dict[str, Any],
        stream: bool = False,
    ):
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

        async for rsp, content in self.request_stream("post", endpoint, args, stream):
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

        rsp, content = await self.request(
            "post",
            "/ai/module/train",
            {
                "data": data,
                "lr": rate,
                "steps": steps,
                "name": name,
                "description": desc,
            },
        )
        self._treat_response_object(rsp, content, 201)

        # TODO: verify response ?

        return content

    async def get_trained_modules(self) -> List[Dict[str, Any]]:
        """
        :return: List of modules trained or in training
        """

        rsp, content = await self.request("get", "/ai/module/all")
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

        rsp, content = await self.request("get", f"/ai/module/{module_id}")
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

        rsp, content = await self.request("delete", f"/ai/module/{module_id}")
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

        rsp, content = await self.request("get", f"/ai/generate-voice?{query}")
        self._treat_response_object(rsp, content, 200)

        return content

    async def suggest_tags(self, tag: str, model: ImageModel):
        assert_type(str, tag=tag)
        assert_type(ImageModel, model=model)

        query = urlencode(
            {
                "model": model,
                "prompt": tag,
            },
            quote_via=quote,
        )

        rsp, content = await self.request("get", f"/ai/generate-image/suggest-tags?{query}")
        self._treat_response_object(rsp, content, 200)

        return content

    async def generate_image(self, prompt: str, model: ImageModel, parameters: Dict[str, Any]) -> AsyncIterable[str]:
        assert_type(str, prompt=prompt)
        assert_type(ImageModel, model=model)
        assert_type(dict, parameters=parameters)

        args = {
            "input": prompt,
            "model": model.value,
            "parameters": parameters,
        }

        async for rsp, content in self.request_stream("post", "/ai/generate-image", args):
            self._treat_response_object(rsp, content, 201)

            yield content
