from typing import Any

from msgpackr.constants import SKIP
from msgpackr.unpack import MsgpackExtension


class NAIExtension(MsgpackExtension):
    @classmethod
    def unpack(cls, _unpacker, _data: bytes, _pos: int, _length: int) -> Any:
        return SKIP

    # TODO: the data should be bundled in post_unpack

    @classmethod
    def pack(cls, _unpacker, data: Any) -> bytes:
        return data


class Ext20(NAIExtension):
    EXT_TYPE = 20


class Ext30(NAIExtension):
    EXT_TYPE = 30


class Ext31(NAIExtension):
    EXT_TYPE = 31


class Ext40(NAIExtension):
    EXT_TYPE = 40


class Ext41(NAIExtension):
    EXT_TYPE = 41


class Ext42(NAIExtension):
    EXT_TYPE = 42
