from http.cookies import SimpleCookie
from logging import Logger
from os.path import abspath, dirname
from typing import Optional

from aiohttp import BasicAuth, ClientSession, ClientTimeout
from aiohttp.typedefs import StrOrURL
from multidict import CIMultiDict

from novelai_api._high_level import HighLevel
from novelai_api._low_level import LowLevel


class NovelAIAPI:
    # Constants

    # TODO: might want to make the base endpoint configurable
    #: The base address for the API
    BASE_ADDRESS: str = "https://api.novelai.net"
    LIB_ROOT: str = dirname(abspath(__file__))

    # Variables

    #: The logger for the API
    logger: Logger
    #: The client session for the API (None if synchronous)
    session: Optional[ClientSession]

    #: The timeout for a request (in seconds)
    timeout: ClientTimeout
    #: The headers for a request
    headers: CIMultiDict
    #: The cookies for a request
    cookies: SimpleCookie
    #: The proxy for a request (None if no proxy)
    proxy: Optional[StrOrURL] = None
    #: The proxy authentication for a request (None if no proxy)
    proxy_auth: Optional[BasicAuth] = None

    # API parts

    #: The low-level API (thin wrapper)
    low_level: LowLevel
    #: The high-level API (abstraction on top of low-level)
    high_level: HighLevel

    def __init__(self, session: Optional[ClientSession] = None, logger: Optional[Logger] = None):
        """
        Create a new NovelAIAPI object, which can be used to interact with the API.
        Use the low_level and high_level attributes for this purpose

        Use attach_session and detach_session to switch between synchronous and asynchronous requests
        by attaching a ClientSession

        :param session: The ClientSession to use for requests (None for synchronous)
        :param logger: The logger to use for the API (None for creating an empty default logger)
        """

        # variable passing
        if session is not None and not isinstance(session, ClientSession):
            raise ValueError(f"Expected None or type 'ClientSession' for session, but got type '{type(session)}'")

        # no session = synchronous
        self.logger = Logger("NovelAI_API") if logger is None else logger
        self.session = session

        self.timeout = ClientTimeout(300)
        self.headers = CIMultiDict()
        self.cookies = SimpleCookie()

        self.proxy = None
        self.proxy_auth = None

        # API parts
        self.low_level = LowLevel(self)
        self.high_level = HighLevel(self)

    def attach_session(self, session: ClientSession):
        """
        Attach a ClientSession, making the requests asynchronous
        """

        if not isinstance(session, ClientSession):
            raise ValueError(f"Expected type 'ClientSession' for session, but got type '{type(session)}'")

        self.session = session

    def detach_session(self):
        """
        Detach the current ClientSession, making the requests synchronous
        """

        self.session = None

    @property
    def timeout(self) -> float:
        """
        Timeout for a request (in seconds)
        """

        return self._timeout.total

    @timeout.setter
    def timeout(self, value: float):
        """
        Timeout for a request (in seconds)
        """

        self._timeout = ClientTimeout(value)
