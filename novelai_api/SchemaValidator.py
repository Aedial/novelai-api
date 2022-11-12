from json import loads
from os import listdir
from os.path import abspath, dirname, join, splitext
from typing import Any, Dict

from jsonschema import RefResolver, validate


class SchemaValidator:
    _schemas: Dict[str, Dict[str, Any]]
    _resolver: RefResolver

    def __init__(self):
        if not hasattr(self, "_schemas"):
            schemas = {}

            lib_root = abspath(dirname(__file__))
            schema_dir = join(lib_root, "schemas")

            for filename in listdir(schema_dir):
                with open(join(schema_dir, filename), encoding="utf-8") as f:
                    schema_key = splitext(filename)[0]

                    schemas[schema_key] = loads(f.read())

            SchemaValidator._schemas = schemas
            SchemaValidator._resolver = RefResolver("", "", store=schemas)

    @classmethod
    def validate(cls, name: str, obj: Any):
        validate(obj, cls._schemas[name], resolver=cls._resolver)


# initialize the schemas. A bit dirty, but the simplest
SchemaValidator()
