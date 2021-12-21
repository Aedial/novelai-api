from multidict import CIMultiDict
from aiohttp import ClientTimeout

class FakeClientSession:
	headers: CIMultiDict
	timeout: ClientTimeout
	cookies: dict

	def __init__(self):
		self.headers = CIMultiDict()
		self.timeout = ClientTimeout(300)
		self.cookies = {}