from aiohttp import ClientSession, ClientError
from aiohttp.client_reqrep import ClientResponse
from aiohttp.client_exceptions import ClientConnectionError

from novelai_api.NovelAIError import NovelAIError
from novelai_api.utils import tokens_to_b64
from novelai_api.Tokenizer import Tokenizer
from novelai_api.SchemaValidator import SchemaValidator
from novelai_api.Preset import Model

from json import loads
from urllib.parse import urlencode, quote

from typing import Union, Dict, Tuple, List, Iterable, Any, NoReturn, Optional


#=== INTERNALS ===#
#=== API ===#
class Low_Level:
    _parent: "NovelAI_API"
    _is_async: bool

    is_schema_validation_enabled: bool

    def __init__(self, parent: "NovelAI_API"):
        self._parent = parent
        self.is_schema_validation_enabled = True

    def _treat_response_object(self, rsp: ClientResponse, content: Any, status: int) -> Any:
        # error is an unexpected fail and usually come with a success status
        if type(content) is dict and "error" in content:
            raise NovelAIError(rsp.status, content["error"])

        # success
        if rsp.status == status:
            return content

        # not success, but valid response
        if type(content) is dict and "message" in content:    # NovelAI REST API error
            raise NovelAIError(rsp.status, content["message"])
        elif hasattr(rsp, "reason"):                        # HTTPException error
            raise NovelAIError(rsp.status, str(rsp.reason))
        else:
            raise NovelAIError(rsp.status, "Unknown error")

    def _treat_response_bool(self, rsp: ClientResponse, content: Any, status: int) -> bool:
        if rsp.status == status:
            return True

        self._treat_response_object(rsp, content, status)
        return False

    async def _treat_response(self, rsp: ClientResponse, data: Any) -> Any:
        if rsp.content_type == "application/json":
            return (await data.json())

        if rsp.content_type == "text/plain":
            return (await data.text())

        if rsp.content_type == "audio/mpeg" or rsp.content_type == "audio/webm":
            return (await data.read())

        raise RuntimeError(f"Unsupported type: {rsp.content_type}")

    def _parse_stream_data(self, stream_content: str) -> Dict[str, Any]:
        stream_data = {}

        for line in stream_content.splitlines():
            colon = line.find(":")
            # TODO: replace by a meaningful error
            assert ":" != -1, f"Malformed data stream line: {line}"

            stream_data[line[:colon]] = line[colon + 1:]

        return stream_data

    async def _treat_response_stream(self, rsp: ClientResponse, data: bytes) -> Any:
        data = data.decode()

        if rsp.content_type == "text/event-stream":
            stream_data = self._parse_stream_data(data)

            # TODO: replace by a meaningful error
            assert "data" in stream_data
            data = loads(stream_data["data"])

        return data

    async def _request(self, method: str, url: str, session: ClientSession,
                             data: Union[Dict[str, Any], str], stream: bool) -> Tuple[ClientResponse, Any]:

        kwargs = {
            "timeout": self._parent._timeout,
            "cookies": self._parent.cookies,
            "headers": self._parent.headers,
        }

        kwargs["json" if type(data) is dict else "data"] = data

        async with session.request(method, url, **kwargs) as rsp:
            if stream:
                async for i in rsp.content.iter_any():
                    yield (rsp, await self._treat_response_stream(rsp, i))
            else:
                yield (rsp, await self._treat_response(rsp, rsp))

    async def request_stream(self, method: str, endpoint: str, data: Optional[Union[Dict[str, Any], str]] = None,
                                   stream: bool = True) -> Tuple[ClientResponse, Any]:
        """
        Send request with support for data streaming

        :param method: Method of the request (get, post, delete)
        :param endpoint: Endpoint of the request
        :param data: Data to pass to the method if needed
        :param stream: Use data streaming for the response
        """

        url = f"{self._parent._BASE_ADDRESS}{endpoint}"

        is_sync = self._parent._session is None
        session = ClientSession() if is_sync else self._parent._session

        try:
            async for i in self._request(method, url, session, data, stream):
                yield i
        except ClientConnectionError as e:      # No internet
            raise NovelAIError(e.errno, str(e))
        # TODO: there may be other request errors to catch
        finally:
            if is_sync:
                await session.close()

    async def request(self, method: str, endpoint: str, data: Optional[Union[Dict[str, Any], str]] = None) -> Tuple[ClientResponse, Any]:
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

    async def register(self, recapcha: str, access_key: str, email: Optional[str], giftkey: Optional[str] = None) -> bool:
        """
        Register a new account

        :param recapcha: Recapcha of the NovelAI website
        :param access_key: Access key of the account
        :param email: Hashed email (used for recovery)
        :param giftkey: Giftkey

        :return: True if success
        """

        assert type(recapcha) is str, f"Expected type 'str' for recapcha, but got type '{type(recapcha)}'"
        assert type(access_key) is str, f"Expected type 'str' for access_key, but got type '{type(access_key)}'"
        assert type(email) in (str, None), f"Expected type 'str' for email, but got type '{type(email)}'"
        assert type(giftkey) in (str, None), f"Expected type 'str' for giftkey, but got type '{type(giftkey)}'"

        assert len(access_key) == 64, f"access_key should be 64 characters, got length of {len(access_key)}"
        assert email is None or len(email) == 64, f"email should be 64 characters, got length of {len(email)}"

        data = { "recapcha": recapcha, "key": access_key }

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

        assert type(access_key) is str, f"Expected type 'str' for access_key, but got type '{type(access_key)}'"

        assert len(access_key) == 64, f"access_key should be 64 characters, got length of {len(access_key)}"

        rsp, content = await self.request("post", "/user/login", { "key": access_key })
        self._treat_response_object(rsp, content, 201)

        if self.is_schema_validation_enabled:
            SchemaValidator.validate("schema_SuccessfulLoginResponse", content)

        return content

    async def change_access_key(self, current_key: str, new_key: str, new_email: Optional[str] = None) -> Dict[str, str]:
        assert type(current_key) is str, f"Expected type 'str' for current_key, but got type '{type(current_key)}'"
        assert type(new_key) is str, f"Expected type 'str' for new_key, but got type '{type(new_key)}'"
        assert new_email is None or type(new_email) is str, f"Expected None or type 'str' for new_email, but got type '{type(new_email)}'"

        assert len(current_key) == 64, f"Current access key should be 64 characters, got length of {len(current_key)}"
        assert len(new_key) == 64, f"New access key should be 64 characters, got length of {len(new_key)}"

        data = { "currentAccessKey": current_key, "newAccessKey": new_key }

        if new_email is not None:
            data["newEmail"] = new_email

        rsp, content = await self.request("post", "/user/change-access-key", data)
        self._treat_response_object(rsp, content, 200)

        if self.is_schema_validation_enabled:
            SchemaValidator.validate("schema_SuccessfulLoginResponse", content)

        return content

    async def send_email_verification(self, email: str) -> bool:
        assert type(email) is str, f"Expected type 'str' for email, but got type '{type(email)}'"

        rsp, content = await self.request("post", "/user/resend-email-verification", { "email": email })
        return self._treat_response_bool(rsp, content, 200)

    async def verify_email(self, verification_token: str) -> bool:
        assert type(verification_token) is str, f"Expected type 'str' for verification_token, but got type '{type(verification_token)}'"

        assert len(verification_token) == 64, f"Verification token should be 64 characters, got length of {len(verification_token)}"

        rsp, content = await self.request("post", "/user/verify-email", { "verificationToken": verification_token })
        return self._treat_response_bool(rsp, content, 200)

    async def get_information(self) -> Dict[str, Any]:
        rsp, content = await self.request("get", "/user/information")
        self._treat_response_object(rsp, content, 200)

        if self.is_schema_validation_enabled:
            SchemaValidator.validate("schema_AccountInformationResponse", content)

        return content

    async def request_account_recovery(self, email: str) -> bool:
        assert type(email) is str, f"Expected type 'str' for email, but got type '{type(email)}'"

        rsp, content = await self.request("post", "/user/recovery/request", { "email": email })
        return self._treat_response_bool(rsp, content, 202)

    async def recover_account(self, recovery_token: str, new_key: str, delete_content: bool = False) -> Dict[str, Any]:
        assert type(recovery_token) is str, f"Expected type 'str' for recovery_token, but got type '{type(recovery_token)}'"
        assert type(new_key) is str, f"Expected type 'str' for new_key, but got type '{type(new_key)}'"
        assert type(delete_content) is bool, f"Expected type 'bool' for delete_content, but got type '{type(delete_content)}'"

        assert 16 <= len(recovery_token), f"Recovery token should be at least 16 characters, got length of {len(recovery_token)}"
        assert len(new_key) == 64, f"New access key should be 64 characters, got length of {len(new_key)}"

        rsp, content = await self.request("post", "/user/recovery/recover", { "recoveryToken": recovery_token, "newAccessKey": new_key, "deleteContent": delete_content })
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
        assert type(keystore) is dict, f"Expected type 'dicy' for keystore, but got type '{type(keystore)}'"

        rsp, content = await self.request("put", "/user/keystore", keystore)
        return self._treat_response_object(rsp, content, 200)

    async def download_objects(self, object_type: str) -> Dict[str, List[Dict[str, Union[str, int]]]]:
        assert type(object_type) is str, f"Expected type 'str' for object_type, but got type '{type(object_type)}'"

        rsp, content = await self.request("get", f"/user/objects/{object_type}")
        self._treat_response_object(rsp, content, 200)

        if self.is_schema_validation_enabled:
            SchemaValidator.validate("schema_ObjectsResponse", content)

        return content

    async def upload_objects(self, object_type: str, meta: str, data: str) -> bool:
        assert type(object_type) is str, f"Expected type 'str' for object_type, but got type '{type(object_type)}'"
        assert type(meta) is str, f"Expected type 'str' for meta, but got type '{type(meta)}'"
        assert type(data) is str, f"Expected type 'str' for data, but got type '{type(data)}'"

        assert len(meta) <= 128, f"Meta should be at most 128 characters, got length of {len(meta)}"

        rsp, content = await self.request("put", f"/user/objects/{object_type}", { "meta": meta, "data": data })
        self._treat_response_object(rsp, content, 200)

        return content

    async def download_object(self, object_type: str, object_id: str) -> Dict[str, Union[str, int]]:
        assert type(object_type) is str, f"Expected type 'str' for object_type, but got type '{type(object_type)}'"
        assert type(object_id) is str, f"Expected type 'str' for object_id, but got type '{type(object_id)}'"

        rsp, content = await self.request("get", f"/user/objects/{object_type}/{object_id}")
        self._treat_response_object(rsp, content, 200)

        if self.is_schema_validation_enabled:
            SchemaValidator.validate("schema_userData", content)

        return content

    async def upload_object(self, object_type: str, object_id: str, meta: str, data: str) -> bool:
        assert type(object_type) is str, f"Expected type 'str' for object_type, but got type '{type(object_type)}'"
        assert type(object_id) is str, f"Expected type 'str' for object_id, but got type '{type(object_id)}'"
        assert type(meta) is str, f"Expected type 'str' for meta, but got type '{type(meta)}'"
        assert type(data) is str, f"Expected type 'str' for data, but got type '{type(data)}'"

        assert len(meta) <= 128, f"Meta should be at most 128 characters, got length of {len(meta)}"

        rsp, content = await self.request("patch", f"/user/objects/{object_type}/{object_id}", { "meta": meta, "data": data })
        self._treat_response_object(rsp, content, 200)

        return content

    async def delete_object(self, object_type: str, object_id: str) -> Dict[str, Union[str, int]]:
        assert type(object_type) is str, f"Expected type 'str' for object_type, but got type '{type(object_type)}'"
        assert type(object_id) is str, f"Expected type 'str' for object_id, but got type '{type(object_id)}'"

        rsp, content = await self.request("delete", f"/user/objects/{object_type}/{object_id}")
        return self._treat_response_object(rsp, content, 200)

    async def get_settings(self) -> str:
        rsp, content = await self.request("get", "/user/clientsettings")
        return self._treat_response_object(rsp, content, 200)

    async def set_settings(self, value: str) -> bool:
        assert type(value) is str, f"Expected type 'str' for value, but got type '{type(value)}'"

        rsp, content = await self.request("put", "/user/clientsettings", value)
        return self._treat_response_bool(rsp, content, 200)

    async def bind_subscription(self, payment_processor: str, subscription_id: str) -> bool:
        assert type(payment_processor) is str, f"Expected type 'str' for payment_processor, but got type '{type(payment_processor)}'"
        assert type(subscription_id) is str, f"Expected type 'str' for subscription_id, but got type '{type(subscription_id)}'"

        rsp, content = await self.request("post", "/user/subscription/bind", { "paymentProcessor": payment_processor, "subscriptionId": subscription_id })
        return self._treat_response_bool(rsp, content, 201)

    async def change_subscription(self, new_plan: str) -> bool:
        assert type(new_plan) is str, f"Expected type 'str' for new_plan, but got type '{type(new_plan)}'"

        rsp, content = await self.request("post", "/user/subscription/change", { "newSubscriptionPlan": new_plan })
        return self._treat_response_bool(rsp, content, 200)

    async def generate(self, input: Union[List[int], str], model: Model, params: Dict[str, Any],
                             stream: bool = False) -> Dict[str, str]:
        """
        :param input: Input to be sent the AI
        :param model: Model of the AI
        :param params: Generation parameters
        :param stream: Use data streaming for the response

        :return: Generated output
        """

        assert isinstance(input, (str, list)), f"Expected type 'str' or 'List[int]' for input, but got type '{type(input)}'"
        assert type(model) is Model, f"Expected type 'Model' for model, but got type '{type(model)}'"
        assert type(params) is dict, f"Expected type 'dict' for params, but got type '{type(params)}'"
        assert type(stream) is bool, f"Expected type 'bool' for stream, but got type '{type(stream)}'"

        if type(input) is str:
            input = Tokenizer.encode(model, input)

        input = tokens_to_b64(input)
        args = { "input": input, "model": model.value, "parameters": params }

        endpoint = "/ai/generate-stream" if stream else "/ai/generate"

        async for rsp, content in self.request_stream("post", endpoint, args, stream):
            self._treat_response_object(rsp, content, 201)

            yield content

    async def classify(self):
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

        assert type(data) is str, f"Expected type 'str' for data, but got type '{type(data)}'"
        assert type(rate) is int, f"Expected type 'int' for rate, but got type '{type(rate)}'"
        assert type(steps) is int, f"Expected type 'int' for steps, but got type '{type(steps)}'"
        assert type(name) is str, f"Expected type 'str' for name, but got type '{type(name)}'"
        assert type(desc) is str, f"Expected type 'str' for desc, but got type '{type(desc)}'"

        rsp, content = await self.request("post", "/ai/module/train", { "data": data, "lr": rate, "steps": steps, "name": name, "description": desc })
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

        assert type(module_id) is str, f"Expected type 'str' for module_id, but got type '{type(module_id)}'"

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

        assert type(module_id) is str, f"Expected type 'str' for module_id, but got type '{type(module_id)}'"

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

        assert type(text) is str, f"Expected type 'str' for text, but got type '{type(text)}'"
        assert type(seed) is str, f"Expected type 'str' for seed, but got type '{type(seed)}'"
        assert type(voice) is int, f"Expected type 'int' for voice, but got type '{type(voice)}'"
        assert type(opus) is bool, f"Expected type 'bool' for opus, but got type '{type(opus)}'"
        assert type(version) is str, f"Expected type 'bool' for version, but got type '{type(version)}'"

        # urlencode keeps capitalization on bool =_=
        opus = "true" if opus else "false"
        query = urlencode({
            "text": text,
            "seed": seed,
            "voice": voice,
            "opus": opus,
            "version": version
        }, quote_via = quote)

        rsp, content = await self.request("get", f"/ai/generate-voice?{query}")
        self._treat_response_object(rsp, content, 200)

        return content
