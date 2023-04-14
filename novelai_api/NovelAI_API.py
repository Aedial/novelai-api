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
    BASE_ADDRESS: str = "https://api.novelai.net"
    LIB_ROOT: str = dirname(abspath(__file__))

    # Variables
    logger: Logger
    session: Optional[ClientSession]

    timeout: ClientTimeout
    headers: CIMultiDict
    cookies: SimpleCookie
    proxy: Optional[StrOrURL] = None
    proxy_auth: Optional[BasicAuth] = None

    low_level: LowLevel
    high_level: HighLevel

    def __init__(self, session: Optional[ClientSession] = None, logger: Optional[Logger] = None):
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
