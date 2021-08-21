from novelai_api.NovelAIError import NovelAIError
from novelai_api._low_level import Low_Level
from novelai_api._high_level import High_Level

from aiohttp import ClientSession

from logging import Logger, NullHandler
from typing import Union, Dict, Tuple, List, Iterable, Any, NoReturn, Optional, MethodDescriptorType

class NovelAI_API:
	# Constants
	_BASE_ADDRESS: str = "https://api.novelai.net"

	# Variables
	_token: Optional[str] = None
	_logger: Logger
	_session: ClientSession

	# Base headers (for user agent, etc)
	base_headers: Dict = {}

	### Low Level Public API
	low_level: Low_Level
	high_level: High_Level

	# === Operators === #
	def __init__(self, session: ClientSession, username: Optional[str] = None, password: Optional[str] = None, logger: Optional[Logger] = None):
		# API parts
		self.low_level = Low_Level(self)
		self.high_level = High_Level(self)

		# variable passing
		self._session = session

		if logger is None:
			self._logger = Logger("NovelAI_API")
			self._logger.addHandler(NullHandler())
		else:
			self._logger = logger

		if username is not None and password is not None:
			self.high_level.login(username, password)
		# if no username and password is given, it'll probably be a late connection
		elif (username is None) ^ (password is None):
			self._logger.warning(f"Username ({username}) or password ({password}) is not set. This is probably an error")