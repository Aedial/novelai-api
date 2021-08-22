from novelai_api.NovelAIError import NovelAIError

from aiohttp import ClientSession, ClientError
from aiohttp.client_reqrep import ClientResponse
from aiohttp.client import _RequestContextManager
from aiohttp.http_exceptions import HttpProcessingError

from typing import Union, Dict, Tuple, List, Iterable, Any, NoReturn, Optional, MethodDescriptorType

#=== INTERNALS ===#
def treat_response_object(rsp: Union[ClientResponse, NovelAIError], content: Any, status: int) -> Union[Any, NovelAIError]:
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
		return NovelAIError(rsp.status, str(rsp.reason))
	else:
		return NovelAIError(rsp.status, "Unknown error")

def treat_response_bool(rsp: Union[ClientResponse, NovelAIError], content: Any, status: int) -> Union[bool, NovelAIError]:
	rsp = treat_response_object(rsp, content, status)
	if type(rsp) is NovelAIError:
		return rsp

	return True

async def treat_response(rsp: ClientResponse) -> Any:
	if rsp.content_type == "application/json":
		return await rsp.json()
	else:
		return await rsp.text()

async def request(self: "NovelAI_API", request_method: MethodDescriptorType, endpoint: str, data: Optional[Union[Dict[str, Any], str]], need_login: bool) -> Union[Tuple[ClientResponse, Any], NovelAIError]:
	"""
	:param url: Endpoint of the request
	:param request_method: Method of the reqest from ClientSession
	:param data: Data to pass to the request_method if needed
	:param need_login: Tell if the request needs the authorization token
	"""

	url = f"{self._BASE_ADDRESS}{endpoint}"

	headers = self.base_headers.copy()
	if need_login:
		assert self._token is not None, f"You need to be log in to use the endpoint {endpoint}"
		headers["Authorization"] = f"Bearer {self._token}"

	try:
		if type(data) is dict:	# data transforms dict in str
			async with request_method(url, json = data, headers = headers) as rsp:
				return (rsp, await treat_response(rsp))
		else:
			async with request_method(url, data = data, headers = headers) as rsp:
				return (rsp, await treat_response(rsp))
	except (ClientError, HttpProcessingError) as e:
		# FIXME: when are these errors triggered ? raise_as_error ?
		return NovelAIError(0, "Unknown error")

async def get(self: "NovelAI_API", endpoint: str, need_login: bool = True) -> Union[Tuple[ClientResponse, Any], NovelAIError]:
	return await request(self, self._session.get, endpoint, None, need_login)

async def post(self: "NovelAI_API", endpoint: str, data: Dict[str, Any], need_login: bool = True) -> Union[Tuple[ClientResponse, Any], NovelAIError]:
	return await request(self, self._session.post, endpoint, data, need_login)

async def put(self: "NovelAI_API", endpoint: str, data: Union[Dict[str, Any], str],need_login: bool = True) -> Union[Tuple[ClientResponse, Any], NovelAIError]:
	return await request(self, self._session.put, endpoint, data, need_login)

async def patch(self: "NovelAI_API", endpoint: str, data: Dict[str, Any], need_login: bool = True) -> Union[Tuple[ClientResponse, Any], NovelAIError]:
	return await request(self, self._session.patch, endpoint, data, need_login)

async def delete(self: "NovelAI_API", endpoint: str, need_login: bool = True) -> Union[Tuple[ClientResponse, Any], NovelAIError]:
	return await request(self, self._session.delete, endpoint, None, need_login)

#=== API ===#
class Low_Level:
	_parent: "NovelAI_API"

	def __init__(self, parent: "NovelAI_API"):
		self._parent = parent

	async def is_reachable(self) -> Union[bool, NovelAIError]:
		"""
		Check if the NovelAI API is reachable

		:return: True if reachable, False if not, NovelAIError on error
		"""
		rsp, content = await get(self._parent, "/", False)
		return treat_response_bool(rsp, content, 200)

	async def register(self, recapcha: str, access_key: str, email: Optional[str], giftkey: Optional[str] = None) -> Union[bool, NovelAIError]:
		"""
		Register a new account

		:param recapcha: Recapcha of the NovelAI website
		:param access_key: Access key of the account
		:param email: Hashed email (used for recovery)
		:param giftkey: Giftkey

		:return: True if success, NovelAIError otherwise
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

		rsp, content = await post(self._parent, "/user/register", data, False)
		rsp = treat_response_bool(rsp, content, 201)
		if type(rsp) is not NovelAIError:
			# FIXME: handle cases where the response is corrupted
			self._parent._token = rsp["accessToken"]

		return rsp

	async def login(self, access_key: str) -> Union[Dict[str, str], NovelAIError]:
		"""
		Log in to the account

		:param access_key: Access key of the account

		:return: True on success, NovelAIError otherwise
		"""

		assert type(access_key) is str, f"Expected type 'str' for access_key, but got type '{type(access_key)}'"

		assert len(access_key) == 64, f"access_key should be 64 characters, got length of {len(access_key)}"

		rsp, content = await post(self._parent, "/user/login", { "key": access_key }, False)
		rsp = treat_response_object(rsp, content, 201)
		if type(rsp) is not NovelAIError:
			# FIXME: handle cases where the response is corrupted
			self._parent._token = rsp["accessToken"]

		return rsp

	async def change_access_key(self, current_key: str, new_key: str) -> Union[bool, NovelAIError]:
		assert type(current_key) is str, f"Expected type 'str' for current_key, but got type '{type(current_key)}'"
		assert type(new_key) is str, f"Expected type 'str' for new_key, but got type '{type(new_key)}'"

		assert len(current_key) == 64, f"Current access key should be 64 characters, got length of {len(current_key)}"
		assert len(new_key) == 64, f"New access key should be 64 characters, got length of {len(new_key)}"

		rsp, content = await post(self._parent, "/user/change-access-key", { "currentAccessKey": current_key, "newAccessKey": new_key })
		return treat_response_bool(rsp, content, 200)

	async def request_account_recovery(self, email: str) -> Union[bool, NovelAIError]:
		assert type(email) is str, f"Expected type 'str' for email, but got type '{type(email)}'"

		rsp, content = await post(self._parent, "/user/recovery/request", { "email": email }, False)
		return treat_response_bool(rsp, content, 202)

	async def recover_account(self, recovery_token: str, new_key: str, delete_content: bool = False) -> Union[bool, NovelAIError]:
		assert type(recovery_token) is str, f"Expected type 'str' for recovery_token, but got type '{type(recovery_token)}'"
		assert type(new_key) is str, f"Expected type 'str' for new_key, but got type '{type(new_key)}'"
		assert type(delete_content) is bool, f"Expected type 'bool' for delete_content, but got type '{type(delete_content)}'"

		assert 16 <= len(recovery_token), f"Recovery token should be at least 16 characters, got length of {len(recovery_token)}"
		assert len(new_key) == 64, f"New access key should be 64 characters, got length of {len(new_key)}"

		rsp, content = await post(self._parent, "//user/recovery/recover", { "recoveryToken": recovery_token, "newAccessKey": new_key, "deleteContent": delete_content }, False)
		return treat_response_bool(rsp, content, 201)

	async def delete_account(self) -> Union[bool, NovelAIError]:
		rsp, content = await post(self._parent, "/user/delete", None)
		return treat_response_bool(rsp, content, 200)

	async def get_priority(self) -> Union[Dict[str, Any], NovelAIError]:
		rsp, content = await get(self._parent, "/user/priority")
		return treat_response_object(rsp, content, 200)

	async def get_subscription(self) -> Union[Dict[str, Any], NovelAIError]:
		rsp, content = await get(self._parent, "/user/subscription")
		return treat_response_object(rsp, content, 200)

	async def get_keystore(self) -> Union[Dict[str, str], NovelAIError]:
		rsp, content = await get(self._parent, "/user/keystore")
		return treat_response_object(rsp, content, 200)

	async def set_keystore(self, value: str) -> Union[bool, NovelAIError]:
		assert type(value) is str, f"Expected type 'str' for keystore, but got type '{type(value)}'"

		rsp, content = await put(self._parent, "/user/keystore", { "keystore": value })
		return treat_response_object(rsp, content, 200)

	async def download_objects(self, object_type: str) -> Union[Dict[str, List[Dict[str, Union[str, int]]]], NovelAIError]:
		assert type(object_type) is str, f"Expected type 'str' for object_type, but got type '{type(object_type)}'"

		rsp, content = await get(self._parent, f"/user/objects/{object_type}")
		return treat_response_object(rsp, content, 200)

	async def upload_objects(self, object_type: str, meta: str, data: str) -> Union[bool, NovelAIError]:
		assert type(object_type) is str, f"Expected type 'str' for object_type, but got type '{type(object_type)}'"
		assert type(meta) is str, f"Expected type 'str' for meta, but got type '{type(meta)}'"
		assert type(data) is str, f"Expected type 'str' for data, but got type '{type(data)}'"

		assert len(meta) <= 128, f"Meta should be at most 128 characters, got length of {len(meta)}"

		rsp, content = await put(self._parent, f"/user/objects/{object_type}", { "meta": meta, "data": data })
		return treat_response_bool(rsp, content, 200)

	async def download_object(self, object_type: str, object_id: str) -> Union[Dict[str, Union[str, int]], NovelAIError]:
		assert type(object_type) is str, f"Expected type 'str' for object_type, but got type '{type(object_type)}'"
		assert type(object_id) is str, f"Expected type 'str' for object_id, but got type '{type(object_id)}'"

		rsp, content = await get(self._parent, f"/user/objects/{object_type}/{object_id}")
		return treat_response_object(rsp, content, 200)

	async def upload_object(self, object_type: str, object_id: str, meta: str, data: str) -> Union[bool, NovelAIError]:
		assert type(object_type) is str, f"Expected type 'str' for object_type, but got type '{type(object_type)}'"
		assert type(object_id) is str, f"Expected type 'str' for object_id, but got type '{type(object_id)}'"
		assert type(meta) is str, f"Expected type 'str' for meta, but got type '{type(meta)}'"
		assert type(data) is str, f"Expected type 'str' for data, but got type '{type(data)}'"

		assert len(meta) <= 128, f"Meta should be at most 128 characters, got length of {len(meta)}"

		rsp, content = await patch(self._parent, f"/user/objects/{object_type}/{object_id}", { "meta": meta, "data": data })
		return treat_response_bool(rsp, content, 200)

	async def delete_object(self, object_type: str, object_id: str) -> Union[Dict[str, Union[str, int]], NovelAIError]:
		assert type(object_type) is str, f"Expected type 'str' for object_type, but got type '{type(object_type)}'"
		assert type(object_id) is str, f"Expected type 'str' for object_id, but got type '{type(object_id)}'"

		rsp, content = await delete(self._parent, f"/user/objects/{object_type}/{object_id}")
		return treat_response_object(rsp, content, 200)

	async def get_settings(self) -> Union[str, NovelAIError]:
		rsp, content = await get(self._parent, "/user/clientsettings")
		return treat_response_object(rsp, content, 200)

	async def set_settings(self, value: str) -> Union[bool, NovelAIError]:
		assert type(value) is str, f"Expected type 'str' for value, but got type '{type(value)}'"

		rsp, content = await put(self._parent, "/user​/clientsettings", value)
		return treat_response_bool(rsp, content, 200)

	async def bind_subscription(self, payment_processor: str, subscription_id: str) -> Union[bool, NovelAIError]:
		assert type(payment_processor) is str, f"Expected type 'str' for payment_processor, but got type '{type(payment_processor)}'"
		assert type(subscription_id) is str, f"Expected type 'str' for subscription_id, but got type '{type(subscription_id)}'"

		rsp, content = await post(self._parent, "/user/subscription/bind", { "paymentProcessor": payment_processor, "subscriptionId": subscription_id })
		return treat_response_bool(rsp, content, 201)

	async def change_subscription(self, new_plan: str) -> Union[bool, NovelAIError]:
		assert type(new_plan) is str, f"Expected type 'str' for new_plan, but got type '{type(new_plan)}'"

		rsp, content = await post(self._parent, "​/user​/subscription​/change", { "newSubscriptionPlan": new_plan })
		return treat_response_bool(rsp, content, 200)

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

		args = { "input": input, "model": model, "parameters": params }

		rsp, content = await post(self._parent, "/ai/generate", args)
		return treat_response_object(rsp, content, 201)

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

		rsp, content = await post(self._parent, "​/ai​/module​/train", { "data": data, "lr": rate, "steps": steps, "name": name, "description": desc })
		return treat_response_object(rsp, content, 201)

	async def get_modules(self) -> Union[List[Dict[str, Any]], NovelAIError]:
		"""
		:return: List of modules saved on the logged account
		"""

		rsp, content = await get(self._parent, "/ai/module/all")
		return treat_response_object(rsp, content, 200)

	async def get_module(self, module_id: str) -> Union[Dict[str, Any], NovelAIError]:
		"""
		:param module_id: Id of the module

		:return: Selected module
		"""

		assert type(module_id) is str, f"Expected type 'str' for module_id, but got type '{type(module_id)}'"

		rsp, content = await get(self._parent, f"/ai/module/{module_id}")
		return treat_response_object(rsp, content, 200)

	async def delete_module(self, module_id: str) -> Union[Dict[str, Any], NovelAIError]:
		"""
		Delete the module with id :ref: `module_id`

		:param module_id: Id of the module

		:return: Module that got deleted
		"""

		assert type(module_id) is str, f"Expected type 'str' for module_id, but got type '{type(module_id)}'"

		rsp, content = await delete(self._parent, f"/ai/module/{module_id}")
		return treat_response_object(rsp, content, 200)