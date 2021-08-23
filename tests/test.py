from novelai_api import NovelAI_API
from aiohttp import ClientSession

from novelai_api.utils import get_encryption_key

from enum import Enum
from random import randrange
from argparse import ArgumentParser
from logging import Logger
from os.path import join
from typing import List, Tuple, NoReturn, Dict, Set, Coroutine

from sys import version_info
if version_info >= (3, 7):
	from asyncio import run
else:
	from asyncio import get_event_loop
	def run(main: Coroutine):
		loop = get_event_loop()
		loop.run_until_complete(main)

class NovelAIEnum(Enum):
	IS_REACHABLE				= 1
	REGISTER					= 2
	LOGIN						= 3
	CHANGE_ACCESS_KEY			= 4
	REQUEST_ACCOUNT_RECOVERY	= 5
	RECOVER_ACCOUNT				= 6
	DELETE_ACCOUNT				= 7
	SUBSCRIPTION				= 8
	PRIORITY					= 9
	KEYSTORE_GET				= 10
	KEYSTORE_SET				= 11
	DOWNLOAD_OBJECTS			= 12
	UPLOAD_OBJECTS				= 13
	DOWNLOAD_OBJECT				= 14
	UPLOAD_OBJECT				= 15
	DELETE_OBJECT				= 16
	SETTINGS_GET				= 17
	SETTINGS_SET				= 18
	BIND_SUBSCRIPTION			= 19
	CHANGE_SUBSCRIPTION			= 20
	GENERATE					= 21
	TRAIN_MODULE				= 22
	MODULES_GET					= 23
	MODULE_GET					= 24
	DELETE_MODULE				= 25

functions_not_used: Set[NovelAIEnum] = set((NovelAIEnum.REGISTER, NovelAIEnum.CHANGE_ACCESS_KEY, NovelAIEnum.REQUEST_ACCOUNT_RECOVERY, NovelAIEnum.RECOVER_ACCOUNT, NovelAIEnum.DELETE_ACCOUNT, NovelAIEnum.BIND_SUBSCRIPTION, NovelAIEnum.CHANGE_SUBSCRIPTION))
functions_no_side_effect: Set[NovelAIEnum] = set((NovelAIEnum.IS_REACHABLE, NovelAIEnum.LOGIN, NovelAIEnum.PRIORITY, NovelAIEnum.PRIORITY, NovelAIEnum.KEYSTORE_GET, NovelAIEnum.DOWNLOAD_OBJECTS, NovelAIEnum.DOWNLOAD_OBJECT, NovelAIEnum.SETTINGS_GET, NovelAIEnum.GENERATE, NovelAIEnum.MODULES_GET, NovelAIEnum.MODULE_GET))
functions_need_no_logged: Set[NovelAIEnum] = set((NovelAIEnum.IS_REACHABLE, NovelAIEnum.REGISTER, NovelAIEnum.LOGIN, NovelAIEnum.REQUEST_ACCOUNT_RECOVERY, NovelAIEnum.RECOVER_ACCOUNT))

async def main():
	is_logged: bool = False

	parser = ArgumentParser()
	parser.add_argument("-n", help = "Number of iterations for the test", type = int, default = 100)
	parser.add_argument("--side-effect", help = "Are the tests allowed to have side effect on the test", action = "store_true")
	parser.add_argument("-l", "--login", help = "Is login allowed", action = "store_true")
	args = parser.parse_args()

	# retrieve credentials
	login_info: List[Tuple[str, str]] = []
	if args.login:
		if args.side_effect:
			filename = join("credentials", "creds_can_login.txt")
		else:
			filename = join("credentials", "creds_can_login.txt")

		with open(filename) as f:
			for line in f.read().splitlines():
				username, password = line.split(',')
				login_info.append((username, password))

	assert not args.login or len(login_info) != 0, "'login_info' can't be empty if login is allowed"

	logger = Logger("NovelAI")
	async with ClientSession() as session:
		api = NovelAI_API(session, logger = logger)

		for _ in range(args.n):
			# build choice list
			choice: Set = set((e for e in NovelAIEnum))

			if not args.side_effect:
				choice.intersection_update(functions_no_side_effect)

			if not args.login:
				choice.discard(NovelAIEnum.LOGIN)

			if not is_logged:
				choice.intersection_update(functions_need_no_logged)

			choice -= functions_not_used

			# choose action in the choice list
			assert len(choice) != 0, "Choice shouldn't be empty"

			action: NovelAIEnum = list(choice)[randrange(0, len(choice))]

			if action == NovelAIEnum.IS_REACHABLE:
				print("NovelAI is reachable" if await api.low_level.is_reachable() else "NovelAI is not reachable")
			elif action == NovelAIEnum.REGISTER:
				# TODO
				pass
			elif action == NovelAIEnum.LOGIN:
				username, password = login_info[randrange(0, len(login_info))]
				l = await api.high_level.login(username, password)
				if l:
					print(f"Logged with {username}")
					is_logged = True
				else:
					print(f"Login:", l)
			elif action == NovelAIEnum.CHANGE_ACCESS_KEY:
				# TODO
				pass
			elif action == NovelAIEnum.REQUEST_ACCOUNT_RECOVERY:
				# TODO
				pass
			elif action == NovelAIEnum.RECOVER_ACCOUNT:
				# TODO
				pass
			elif action == NovelAIEnum.DELETE_ACCOUNT:
				# TODO
				pass
			elif action == NovelAIEnum.SUBSCRIPTION:
				print(f"Subscription = {await api.low_level.get_subscription()}")
			elif action == NovelAIEnum.PRIORITY:
				print(f"Priority = {await api.low_level.get_priority()}")
			elif action == NovelAIEnum.KEYSTORE_GET:
				print(f"Keystore = {await api.high_level.get_keystore(get_encryption_key(username, password))}")
			elif action == NovelAIEnum.KEYSTORE_SET:
				# TODO
				pass
			elif action == NovelAIEnum.DOWNLOAD_OBJECTS:
				# TODO
				pass
			elif action == NovelAIEnum.UPLOAD_OBJECTS:
				# TODO
				pass
			elif action == NovelAIEnum.DOWNLOAD_OBJECT:
				# TODO
				pass
			elif action == NovelAIEnum.UPLOAD_OBJECT:
				# TODO
				pass
			elif action == NovelAIEnum.DELETE_OBJECT:
				# TODO
				pass
			elif action == NovelAIEnum.SETTINGS_GET:
				print(f"Settings = {await api.low_level.get_settings()}")
			elif action == NovelAIEnum.SETTINGS_SET:
				# TODO
				pass
			elif action == NovelAIEnum.BIND_SUBSCRIPTION:
				# TODO
				pass
			elif action == NovelAIEnum.CHANGE_SUBSCRIPTION:
				# TODO
				pass
			elif action == NovelAIEnum.GENERATE:
				print(await api.low_level.generate("***", "6B-v3", {
					"temperature": 1,
					"min_length": 10,
					"max_length": 30
				}))
			elif action == NovelAIEnum.TRAIN_MODULE:
				# TODO
				pass
			elif action == NovelAIEnum.MODULES_GET:
				# TODO
				pass
			elif action == NovelAIEnum.MODULE_GET:
				# TODO
				pass
			elif action == NovelAIEnum.DELETE_MODULE:
				# TODO
				pass
			else:
				raise RuntimeError(f"Unknown enum value: {action}")

if __name__ == "__main__":
	run(main())	