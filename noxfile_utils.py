import json
import pathlib
from sys import argv


def get_wheel_path():
    # pylint: disable=C0415,E0401,E0611
    from poetry.core.masonry.api import WheelBuilder
    from poetry.factory import Factory

    poetry = Factory().create_poetry()
    wheel = WheelBuilder(poetry)
    package_file = pathlib.Path("dist") / wheel.wheel_filename

    return package_file


def get_dotenv():
    # load the env vars from a .env, if any
    from dotenv import dotenv_values  # pylint: disable=C0415,E0401,E0611

    return json.dumps(dotenv_values(), ensure_ascii=False)


if __name__ == "__main__" and 2 <= len(argv):
    action = argv[1]

    if action == "wheel_path":
        print(get_wheel_path())
    elif action == "dotenv":
        print(get_dotenv())
