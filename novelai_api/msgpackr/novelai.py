import collections.abc
import datetime
import json

from novelai_api.msgpackr.extensions import MsgPackrExtension
from novelai_api.msgpackr.unpacker import MsgPackrUnpack


class NovelAiUnpacker(MsgPackrUnpack):
    def __init__(self):
        super().__init__()
        self.add_extension(Ext20)
        self.add_extension(Ext30)
        self.add_extension(Ext31)
        self.add_extension(Ext40)
        self.add_extension(Ext41)
        self.add_extension(Ext42)

    # DateTime/Default object handler for JSON output
    def _stringify_handler(*args):
        if isinstance(args[0], datetime.datetime):
            # normalize DateTime strings to ISO, stripping Timezone
            s = args[0].isoformat()[0:26]
            # strip trailing zeros from floating point nanoseconds
            return s.rstrip("0").rstrip(".") if "." in s else s

        # Object is not datetime, so just return as string
        return str(args[0])

    # helper to normalize values and output a consistent JSON string
    def stringify(self, obj):
        new_obj = Ext20(self)._remap_keys(obj)  # any NovelAiExtension will work, we just need the remapper
        return json.dumps(new_obj, default=NovelAiUnpacker._stringify_handler)


class NovelAiExtension(MsgPackrExtension):
    def __init__(self, code, reader):
        super(NovelAiExtension, self).__init__(code, reader)
        self.set_read_handler(self._handler)

    # remaps any floating point keys or values to remove trailing zeros
    def _remap_keys(self, obj):
        if isinstance(obj, dict):
            # object is mapped, so parse key/value pairs
            new_obj = {}
            for key in obj:
                orig_key = key
                if isinstance(key, float):
                    # key is a float, so strip trailing zeros and convert to int if needed
                    s = str(key)
                    key = s.rstrip("0").rstrip(".") if "." in s else s
                    key = float(key) if "." in key else int(key)
                new_obj[key] = self._remap_keys(obj[orig_key])
            return new_obj
        elif isinstance(obj, collections.abc.Sequence) and (not isinstance(obj, str)):
            # object is array, so parse values
            new_obj = []
            for i in range(len(obj)):
                new_obj.append(self._remap_keys(obj[i]))
            return new_obj
        elif isinstance(obj, float):
            # object is a float, so strip trailing zeros and convert to int if needed
            s = str(obj)
            s = s.rstrip("0").rstrip(".") if "." in s else obj
            obj = float(s) if "." in s else int(s)
        return obj

    def _handler(self, *args):
        return self._remap_keys(args[0])


class Ext20(NovelAiExtension):
    def __init__(self, reader):
        super(Ext20, self).__init__(20, reader)


class Ext30(NovelAiExtension):
    def __init__(self, reader):
        super(Ext30, self).__init__(30, reader)


class Ext31(NovelAiExtension):
    def __init__(self, reader):
        super(Ext31, self).__init__(31, reader)


class Ext40(NovelAiExtension):
    def __init__(self, reader):
        super(Ext40, self).__init__(40, reader)


class Ext41(NovelAiExtension):
    def __init__(self, reader):
        super(Ext41, self).__init__(41, reader)


class Ext42(NovelAiExtension):
    def __init__(self, reader):
        super(Ext42, self).__init__(42, reader)
