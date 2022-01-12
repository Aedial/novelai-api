from jsonschema import validate
from json import loads
from os import listdir
from os.path import splitext, dirname, abspath, join

from typing import Any, Dict

class SchemaValidator:
	_schemas: Dict[str, Dict[str, Any]]

	def __init__(self):
		if not hasattr(self, "_schemas"):
			schemas = {}

			lib_root = dirname(abspath(__file__))

			for filename in listdir(join(lib_root, "schemas")):
				with open(join(lib_root, "schemas", filename)) as f:
					schemas[splitext(filename)[0]] = loads(f.read())

			SchemaValidator._schemas = schemas

	@classmethod
	def validate(cls, name: str, obj: Any):
		validate(cls._schemas[name], obj)

# initialize the schemas. A bit dirty, but the simplest
SchemaValidator()