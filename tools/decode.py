from base64 import b64decode
from os.path import abspath, dirname, join
from sys import argv, path

# pylint: disable=C0413,C0415
path.insert(0, abspath(join(dirname(__file__), "..")))
from novelai_api.Preset import Model
from novelai_api.Tokenizer import Tokenizer

assert 2 <= len(argv), "Expected argument"

tokens = b64decode(argv[1])
tokens = [int.from_bytes(tokens[i * 2 : (i + 1) * 2], "little") for i in range(len(tokens) // 2)]
print(f"Tokens = {tokens}")

text = Tokenizer.decode(Model.HypeBot, tokens)
print(f"Text = {text}")
