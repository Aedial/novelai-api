from aiohttp import ClientSession, ClientError
from aiohttp.client_reqrep import ClientResponse
from aiohttp.client import _RequestContextManager
from aiohttp.http_exceptions import HttpProcessingError

from logging import Logger, NullHandler
from hashlib import blake2b, sha256
from argon2 import hash_password_raw
from argon2 import low_level
from base64 import b64encode

from typing import Union, Dict, Tuple, List, Iterable, Any, NoReturn, Optional, MethodDescriptorType

class NovelAIError:
	status: int
	message: str

	def __init__(self, status: int, message: str) -> None:
		self.status = status
		self.message = message

	def __str__(self) -> str:
		return f"{self.status} - {self.message}"

	def __bool__(self) -> bool:
		return False

class NovelAI_API:
	# Constants
	_BASE_ADDRESS: str = "https://api.novelai.net"

	# Variables
	_token: Optional[str] = None
	_logger: Logger = None
	_session: ClientSession = None

	# FIXME: add base headers dictionnary (for user agent, etc)

	# === Operators === #
	def __init__(self, session: ClientSession, username: str = None, password: str = None, logger: Logger = None):
		self._session = session

		if logger is None:
			self._logger = Logger("NovelAI_API")
			self._logger.addHandler(NullHandler())
		else:
			self._logger = logger

		if username is not None and password is not None:
			self.login(username, password)
		# if no username and password is given, it'll probably be a late connection
		elif (username is None) ^ (password is None):
			self._logger.warning(f"Username ({username}) or password ({password}) is not set. This is probably an error")

	# === Internal functions === #
	@staticmethod
	async def _treat_response_object(rsp: Union[ClientResponse, NovelAIError], content: Any, status: int) -> Union[Any, NovelAIError]:
		# error during _request
		if type(rsp) is NovelAIError:
			return rsp

		assert type(rsp) is ClientResponse

		# success
		if rsp.status == status:
			return content

		# not success, but valid response
		if type(content) is dict and "message" in content:	# NovelAI REST API error
			return NovelAIError(rsp.status, content["message"])
		elif hasattr(rsp, "reason"):						# HTTPException error
			return NovelAIError(rsp.status, rsp.reason)
		else:
			return NovelAIError(rsp.status, "Unknown error")

	@classmethod
	async def _treat_response_bool(cls, rsp: Union[ClientResponse, NovelAIError], content: Any, status: int) -> Union[bool, NovelAIError]:
		rsp = await cls._treat_response_object(rsp, content, status)
		if type(rsp) is NovelAIError:
			return rsp

		return True

	@classmethod
	async def _treat_response(cls, rsp: ClientResponse) -> Any:
		if rsp.content_type == "application/json":
			return await rsp.json()
		else:
			return await rsp.text()

	async def _request(self, request_method: MethodDescriptorType, endpoint: str, data: Optional[Union[Dict[str, Any], str]], need_login: bool) -> Union[ClientResponse, NovelAIError]:
		"""
		:param url: Endpoint of the request
		:param request_method: Method of the reqest from ClientSession
		:param data: Data to pass to the request_method if needed
		:param need_login: Tell if the request needs the authorization token
		"""

		url = f"{self._BASE_ADDRESS}{endpoint}"

		headers = { }
		if need_login:
			assert self._token is not None, f"You need to be log in to use the endpoint {endpoint}"
			headers["Authorization"] = f"Bearer {self._token}"

		try:
			async with request_method(url, data = data, headers = headers) as rsp:
				return (rsp, await self._treat_response(rsp))

		except (ClientError, HttpProcessingError) as e:
			# FIXME: when are these errors triggered ? raise_as_error ?
			return NovelAIError(None, None)

	async def _get(self, endpoint: str, need_login: bool = True) -> Union[ClientResponse, NovelAIError]:
		return await self._request(self._session.get, endpoint, None, need_login)

	async def _post(self, endpoint: str, data: Dict[str, Any], need_login: bool = True) -> Union[ClientResponse, NovelAIError]:
		return await self._request(self._session.post, endpoint, data, need_login)

	async def _put(self, endpoint: str, data: Union[Dict[str, Any], str], need_login: bool = True) -> Union[ClientResponse, NovelAIError]:
		return await self._request(self._session.put, endpoint, data, need_login)

	async def _patch(self, endpoint: str, data: Dict[str, Any], need_login: bool = True) -> Union[ClientResponse, NovelAIError]:
		return await self._request(self._session.patch, endpoint, data, need_login)

	async def _delete(self, endpoint: str, need_login: bool = True) -> Union[ClientResponse, NovelAIError]:
		return await self._request(self._session.delete, endpoint, None, need_login)

	@staticmethod
	def _argon_hash(email: str, password: str, size: int, domain: str) -> str:
		data = password[:6] + email + domain

		# salt
		blake = blake2b(digest_size = 16)
		blake.update(data.encode())
		salt = blake.digest()

		# hash
		raw = low_level.hash_secret_raw(password.encode(), salt, 2, int(2000000/1024), 1, size, low_level.Type.ID)
		hashed = b64encode(raw).decode()[:size]

		return hashed

	# === Utilities === #
	@classmethod
	def get_access_key(cls, email: str, password: str):
		return cls._argon_hash(email, password, 64, "novelai_data_access_key").replace('/', '_').replace('+', '-')

	@classmethod
	def get_encryption_key(cls, email: str, password: str):
		return cls._argon_hash(email, password, 128, "novelai_data_encryption_key")

	# === Public API === #
	@property
	async def is_reachable(self) -> Union[bool, NovelAIError]:
		"""
		Check if the NovelAI API is reachable

		:return: True if reachable, False if not, NovelAIError on error
		"""
		rsp, content = await self._get("/", False)
		return await self._treat_response_bool(rsp, content, 200)

	async def register(self, recapcha: str, email: str, password: str, send_mail: bool = True, giftkey: Optional[str] = None) -> Union[bool, NovelAIError]:
		"""
		Register a new account

		:param recapcha: Recapcha of the NovelAI website
		:param email: Email of the account (username)
		:param password: Password of the account
		:param send_mail: Send the mail (hashed and used for recovery)
		:param giftkey: Giftkey

		:return: True if success, NovelAIError otherwise
		"""

		assert type(recapcha) is str, f"Expected type 'str' for recapcha, but got type '{type(recapcha)}'"
		assert type(email) is str, f"Expected type 'str' for email, but got type '{type(email)}'"
		assert type(password) is str, f"Expected type 'str' for password, but got type '{type(password)}'"
		assert type(send_mail) is bool, f"Expected type 'bool' for send_mail, but got type '{type(send_mail)}'"
		assert type(giftkey) in (str, None), f"Expected type 'str' for giftkey, but got type '{type(giftkey)}'"

		key = self.get_access_key(email, password)
		data = { "recapcha": recapcha, "key": key }

		if send_mail:
			data["email"] = email
		if giftkey is not None:
			data["giftkey"] = giftkey

		rsp, content = await self._post("/user/register", data, False)
		rsp = await self._treat_response_bool(rsp, content, 201)
		if type(rsp) is not NovelAIError:
			# FIXME: handle cases where the response is corrupted
			self._token = rsp["accessToken"]

		return rsp

	async def login(self, email: str, password: str) -> Union[bool, NovelAIError]:
		"""
		Log in to the account

		:param email: Email of the account (username)
		:param password: Password of the account

		:return: True on success, NovelAIError otherwise
		"""
		assert type(email) is str, f"Expected type 'str' for email, but got type '{type(email)}'"
		assert type(password) is str, f"Expected type 'str' for password, but got type '{type(password)}'"

		access_key = self.get_access_key(email, password)
		rsp, content = await self._post("/user/login", { "key": access_key }, False)
		rsp = await self._treat_response_object(rsp, content, 201)
		if type(rsp) is not NovelAIError:
			# FIXME: handle cases where the response is corrupted
			self._token = rsp["accessToken"]

		return rsp

	async def change_access_key(self, current_key: str, new_key: str) -> Union[bool, NovelAIError]:
		assert type(current_key) is str, f"Expected type 'str' for current_key, but got type '{type(current_key)}'"
		assert type(new_key) is str, f"Expected type 'str' for new_key, but got type '{type(new_key)}'"

		assert len(current_key) == 64, f"Current access key should be 64 characters, got length of {len(current_key)}"
		assert len(new_key) == 64, f"New access key should be 64 characters, got length of {len(new_key)}"

		rsp, content = await self._post("/user/change-access-key", { "currentAccessKey": current_key, "newAccessKey": new_key })
		return await self._treat_response_bool(rsp, content, 200)

	async def request_account_recovery(self, email: str) -> Union[bool, NovelAIError]:
		assert type(email) is str, f"Expected type 'str' for email, but got type '{type(email)}'"

		rsp, content = await self._post("/user/recovery/request", { "email": email }, False)
		return await self._treat_response_bool(rsp, content, 202)

	async def recover_account(self, recovery_token: str, new_key: str, delete_content: bool = False) -> Union[bool, NovelAIError]:
		assert type(recovery_token) is str, f"Expected type 'str' for recovery_token, but got type '{type(recovery_token)}'"
		assert type(new_key) is str, f"Expected type 'str' for new_key, but got type '{type(new_key)}'"
		assert type(delete_content) is bool, f"Expected type 'bool' for delete_content, but got type '{type(delete_content)}'"

		assert 16 <= len(recovery_token), f"Recovery token should be at least 16 characters, got length of {len(recovery_token)}"
		assert len(new_key) == 64, f"New access key should be 64 characters, got length of {len(new_key)}"

		rsp, content = await self._post("//user/recovery/recover", { "recoveryToken": recovery_token, "newAccessKey": new_key, "deleteContent": delete_content }, False)
		return await self._treat_response_bool(rsp, content, 201)

	async def delete_account(self) -> Union[bool, NovelAIError]:
		rsp, content = await self._post("/user/delete", None)
		return await self._treat_response_bool(rsp, content, 200)

	# FIXME: replace Any in return type
	@property
	async def priority(self) -> Union[Dict[str, Any], NovelAIError]:
		rsp, content = await self._get("/user/priority")
		return await self._treat_response_object(rsp, content, 200)

	# FIXME: replace Any in return type
	@property
	async def subscription(self) -> Union[Dict[str, Any], NovelAIError]:
		rsp, content = await self._get("/user/subscription")
		return await self._treat_response_object(rsp, content, 200)

	@property
	async def keystore(self) -> Union[Dict[str, str], NovelAIError]:
		rsp, content = await self._get("/user/keystore")
		return await self._treat_response_object(rsp, content, 200)

	async def set_keystore(self, value: str) -> Union[bool, NovelAIError]:
		assert type(value) is str, f"Expected type 'str' for keystore, but got type '{type(value)}'"

		rsp, content = await self._put("/user/keystore", { "keystore": value })
		return await self._treat_response_object(rsp, content, 200)

	async def download_objects(self, object_type: str) -> Union[Dict[str, List[Dict[str, Union[str, int]]]], NovelAIError]:
		assert type(object_type) is str, f"Expected type 'str' for object_type, but got type '{type(object_type)}'"

		rsp, content = await self._get(f"/user/objects/{object_type}")
		return await self._treat_response_object(rsp, content, 200)

	async def upload_objects(self, object_type: str, meta: str, data: str) -> Union[bool, NovelAIError]:
		assert type(object_type) is str, f"Expected type 'str' for object_type, but got type '{type(object_type)}'"
		assert type(meta) is str, f"Expected type 'str' for meta, but got type '{type(meta)}'"
		assert type(data) is str, f"Expected type 'str' for data, but got type '{type(data)}'"

		assert len(meta) <= 128, f"Meta should be at most 128 characters, got length of {len(meta)}"

		rsp, content = await self._put(f"/user/objects/{object_type}", { "meta": meta, "data": data })
		return await self._treat_response_bool(rsp, content, 200)

	async def download_object(self, object_type: str, object_id: str) -> Union[Dict[str, Union[str, int]], NovelAIError]:
		assert type(object_type) is str, f"Expected type 'str' for object_type, but got type '{type(object_type)}'"
		assert type(object_id) is str, f"Expected type 'str' for object_id, but got type '{type(object_id)}'"

		rsp, content = await self._get(f"/user/objects/{object_type}/{object_id}")
		return await self._treat_response_object(rsp, content, 200)

	async def upload_object(self, object_type: str, object_id: str, meta: str, data: str) -> Union[bool, NovelAIError]:
		assert type(object_type) is str, f"Expected type 'str' for object_type, but got type '{type(object_type)}'"
		assert type(object_id) is str, f"Expected type 'str' for object_id, but got type '{type(object_id)}'"
		assert type(meta) is str, f"Expected type 'str' for meta, but got type '{type(meta)}'"
		assert type(data) is str, f"Expected type 'str' for data, but got type '{type(data)}'"

		assert len(meta) <= 128, f"Meta should be at most 128 characters, got length of {len(meta)}"

		rsp, content = await self._patch(f"/user/objects/{object_type}/{object_id}", { "meta": meta, "data": data })
		return await self._treat_response_bool(rsp, content, 200)

	async def delete_object(self, object_type: str, object_id: str) -> Union[Dict[str, Union[str, int]], NovelAIError]:
		assert type(object_type) is str, f"Expected type 'str' for object_type, but got type '{type(object_type)}'"
		assert type(object_id) is str, f"Expected type 'str' for object_id, but got type '{type(object_id)}'"

		rsp, content = await self._delete(f"/user/objects/{object_type}/{object_id}")
		return await self._treat_response_object(rsp, content, 200)

	@property
	async def settings(self) -> Union[str, NovelAIError]:
		rsp, content = await self._get("/user/clientsettings")
		return await self._treat_response_object(rsp, content, 200)

	async def set_settings(self, value: str) -> Union[bool, NovelAIError]:
		assert type(value) is str, f"Expected type 'str' for value, but got type '{type(value)}'"

		rsp, content = await self._put("/user​/clientsettings", value)
		return await self._treat_response_bool(rsp, content, 200)

	async def bind_subscription(self, payment_processor: str, subscription_id: str) -> Union[bool, NovelAIError]:
		assert type(payment_processor) is str, f"Expected type 'str' for payment_processor, but got type '{type(payment_processor)}'"
		assert type(subscription_id) is str, f"Expected type 'str' for subscription_id, but got type '{type(subscription_id)}'"

		rsp, content = await self._post("/user/subscription/bind", { "paymentProcessor": payment_processor, "subscriptionId": subscription_id })
		return await self._treat_response_bool(rsp, content, 201)

	async def change_subscription(self, new_plan: str) -> Union[bool, NovelAIError]:
		assert type(new_plan) is str, f"Expected type 'str' for new_plan, but got type '{type(new_plan)}'"

		rsp, content = await self._post("​/user​/subscription​/change", { "newSubscriptionPlan": new_plan })
		return await self._treat_response_bool(rsp, content, 200)

	async def generate(self, input: str, model: str, params: Dict[str, Any]) -> Union[Dict[str, str], NovelAIError]:
		"""
		:param input: Input to be sent the AI
		:param model: Model of the AI
		:param params: Generation parameters

		:return: Generated output
		"""

		assert type(input) is str, f"Expected type 'str' for input, but got type '{type(input)}'"
		assert type(model) is str, f"Expected type 'str' for model, but got type '{type(model)}'"
		assert type(params) is dict, f"Expected type 'dict' for params, but got type '{type(params)}'"

		# TODO: put the option for tokenized input
		params["use_string"] = True

		rsp, content = await self._post("/ai/generate", { "input": input, "model": model, "parameters": params })
		return await self._treat_response_object(rsp, content, 201)

	async def generate_stream(self):
		raise NotImplementedError("Function is not implemented yet")

	async def classify(self):
		raise NotImplementedError("Function is not implemented yet")

	async def train_module(self, data: str, rate: int, steps: int, name: str, desc: str) -> Union[Dict[str, Any], NovelAIError]:
		"""
		:param data: Dataset of the module, in one single string
		:param rate: Learning rate of the training
		:param steps: Number of steps to train the module for
		:param name: Name of the module
		:param desc: Description of the module

		:return: Module being trained
		"""

		assert type(data) is str, f"Expected type 'str' for data, but got type '{type(data)}'"
		assert type(rate) is int, f"Expected type 'int' for rate, but got type '{type(rate)}'"
		assert type(steps) is int, f"Expected type 'int' for steps, but got type '{type(steps)}'"
		assert type(name) is str, f"Expected type 'str' for name, but got type '{type(name)}'"
		assert type(desc) is str, f"Expected type 'str' for desc, but got type '{type(desc)}'"

		rsp, content = await self._post("​/ai​/module​/train", { "data": data, "lr": rate, "steps": steps, "name": name, "description": desc })
		return await self._treat_response_object(rsp, content, 201)

	@property
	async def modules(self) -> Union[List[Dict[str, Any]], NovelAIError]:
		"""
		:return: List of modules saved on the logged account
		"""

		rsp, content = await self._get("/ai/module/all")
		return await self._treat_response_object(rsp, content, 200)

	async def get_module(self, module_id: str) -> Union[Dict[str, Any], NovelAIError]:
		"""
		:param module_id: Id of the module

		:return: Selected module
		"""

		assert type(module_id) is str, f"Expected type 'str' for module_id, but got type '{type(module_id)}'"

		rsp, content = await self._get(f"/ai/module/{module_id}")
		return await self._treat_response_object(rsp, content, 200)

	async def delete_module(self, module_id: str) -> Union[Dict[str, Any], NovelAIError]:
		"""
		Delete the module with id :ref: `module_id`

		:param module_id: Id of the module

		:return: Module that got deleted
		"""

		assert type(module_id) is str, f"Expected type 'str' for module_id, but got type '{type(module_id)}'"

		rsp, content = await self._delete(f"/ai/module/{module_id}")
		return await self._treat_response_object(rsp, content, 200)