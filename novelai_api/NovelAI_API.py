from novelai_api.NovelAIError import NovelAIError
from novelai_api.FakeClientSession import FakeClientSession
from novelai_api._low_level import Low_Level
from novelai_api._high_level import High_Level

from aiohttp import ClientSession, ClientTimeout, ClientTimeout
from multidict import CIMultiDict

from logging import Logger, NullHandler
from typing import Union, Dict, Tuple, List, Iterable, Any, NoReturn, Optional, MethodDescriptorType

from os.path import dirname, abspath

class NovelAI_API:
	# Constants
	_BASE_ADDRESS: str = "https://api.novelai.net"

	# Variables
	_token: Optional[str] = None
	_logger: Logger
	_session: ClientSession
	_timeout: ClientTimeout
	_is_async: bool

	_lib_root: str = dirname(abspath(__file__))

	### Low Level Public API
	low_level: Low_Level
	high_level: High_Level

	# === Operators === #
	def __init__(self, session: Optional[ClientSession] = None, logger: Optional[Logger] = None):
		# variable passing

		# no session = synchronous
		self._is_async = (session is not None)
		if self._is_async:
			self._session = session
		else:
			self._session = FakeClientSession()

		if logger is None:
			self._logger = Logger("NovelAI_API")
			self._logger.addHandler(NullHandler())
		else:
			self._logger = logger

		self._timeout = ClientTimeout(300)

		# API parts
		self.low_level = Low_Level(self)
		self.high_level = High_Level(self)

	def attach_session(self, session: ClientSession) -> NoReturn:
		"""
		Attach a ClientSession, making the requests asynchronous
		"""

		session.headers.update(self._session.headers)
		session.cookie_jar.update_cookies(self._session.cookie_jar)

		self._is_async = True
		self._session = session

	def detach_session(self) -> NoReturn:
		"""
		Detach the current ClientSession, making the requests synchronous
		"""

		session = FakeClientSession()

		session.headers.update(self._session.headers)
		session.cookie_jar.update_cookies(self._session.cookie_jar)

		self._is_async = False
		self._session = session

	@property
	def headers(self) -> CIMultiDict:
		"""
		Headers of the HTTP requests
		"""

		return self._session.headers

	@property
	def timeout(self):
		"""
		Timeout for a request (in seconds)
		"""

		if self._timeout is None or self._timeout.total is None:
			return 300	# aiohttp's default

		return self._timeout.total

	@timeout.setter
	def timeout(self, value: int):
		"""
		Timeout for a request (in seconds)
		"""

		self._timeout = ClientTimeout(value)