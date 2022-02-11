from novelai_api.NovelAIError import NovelAIError
from novelai_api._low_level import Low_Level
from novelai_api._high_level import High_Level

from aiohttp import ClientSession, ClientTimeout, ClientTimeout, CookieJar
from multidict import CIMultiDict

from logging import Logger, NullHandler
from typing import Union, Dict, Tuple, List, Iterable, Any, NoReturn, Optional, MethodDescriptorType

from os.path import dirname, abspath

class NovelAI_API:
	# Constants
	_BASE_ADDRESS: str = "https://api.novelai.net"

	# Variables
	_logger: Logger
	_session: Optional[ClientSession]
	_is_async: bool

	_lib_root: str = dirname(abspath(__file__))

	_timeout: ClientTimeout
	_headers: CIMultiDict
	_cookies: CookieJar

	### Low Level Public API
	low_level: Low_Level
	high_level: High_Level

	# === Operators === #
	def __init__(self, session: Optional[ClientSession] = None, logger: Optional[Logger] = None):
		# variable passing

		# no session = synchronous
		self._is_async = (session is not None)
		self._session = session

		if logger is None:
			self._logger = Logger("NovelAI_API")
		else:
			self._logger = logger

		self._timeout = ClientTimeout()
		self._headers = CIMultiDict()
		self._cookies = CookieJar()

		# API parts
		self.low_level = Low_Level(self)
		self.high_level = High_Level(self)

	def attach_session(self, session: ClientSession) -> NoReturn:
		"""
		Attach a ClientSession, making the requests asynchronous
		"""

		assert session is not None

		self._is_async = True
		self._session = session

	def detach_session(self) -> NoReturn:
		"""
		Detach the current ClientSession, making the requests synchronous
		"""

		self._is_async = False
		self._session = None

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

		return self._timeout.total

	@timeout.setter
	def timeout(self, value: int):
		"""
		Timeout for a request (in seconds)
		"""

		self._timeout = ClientTimeout(value)