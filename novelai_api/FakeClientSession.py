from multidict import CIMultiDict
from aiohttp import CookieJar

class FakeClientSession:
	headers: CIMultiDict
	cookies: CookieJar

	def __init__(self):
		self.headers = CIMultiDict()
		self.cookie_jar = CookieJar()