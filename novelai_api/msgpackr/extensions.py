import collections.abc
import datetime
import struct


class BundledStringsModel:
    def __init__(self):
        self.strings = ["", ""]
        self.position0 = 0
        self.position1 = 0
        self.post_bundle_position = 0


class MsgPackrExtension:
    def __init__(self, code, reader):
        # Main msgpack Unpacker
        self._reader = reader
        self._code = code
        self.read = None
        self.unpack = None
        self.no_buffer = False
        self.use_debug = False

    def set_read_handler(self, handler):
        self.read = handler

    def set_unpack_handler(self, handler):
        self.unpack = handler

    def get_type(self):
        return self._code

    def can_read(self):
        return callable(self.read)

    def can_unpack(self):
        return callable(self.unpack)

    def default_passthrough_handler(self, *args):
        return args[0]


# region MessagePack 1.10.0 Default Extensions


# Extension 0x00
class Ext0(MsgPackrExtension):
    def __init__(self, reader):
        super().__init__(0x00, reader)
        self.set_unpack_handler(self._handler)

    def _handler(self, *args):
        return None


# Extension 0x42
class Ext66(MsgPackrExtension):
    def __init__(self, reader):
        super().__init__(0x42, reader)
        self.set_unpack_handler(self._handler)

    def _handler(self, *args):
        raise NotImplementedError


# Extension 0x62
class Ext98(MsgPackrExtension):
    def __init__(self, reader):
        super(Ext98, self).__init__(98, reader)
        self.set_unpack_handler(self._handler)

    def _handler(self, *args):
        if args[0] is None or isinstance(args[0], bytes) or len(args[0]) < 4:
            raise Exception(f"Invalid argument for extension {self._code}")

        offset = self._reader.position
        orig_offset = offset
        data = args[0]
        n = (data[0] << 24) + (data[1] << 16) + (data[2] << 8) + data[3]
        offset += n - len(data)
        self._reader.seek(offset)

        model = BundledStringsModel()
        self._reader.bundled_strings = model
        model.strings[0] = self._reader.read_only_js_string() or ""
        model.strings[1] = self._reader.read_only_js_string() or ""
        model.position0 = 0
        model.position1 = 0
        model.post_bundle_position = self._reader.position
        self._reader.seek(orig_offset)

        return self._reader.read()


# Extension 0x65
class Ext101(MsgPackrExtension):
    def __init__(self, reader):
        super().__init__(0x65, reader)
        self.set_unpack_handler(self._handler)

    def _handler(self, *args):
        raise NotImplementedError


# Extension 0x69
class Ext105(MsgPackrExtension):
    def __init__(self, reader):
        super().__init__(0x69, reader)
        self.set_unpack_handler(self._handler)

    def _handler(self, *args):
        raise NotImplementedError


# Extension 0x70
class Ext112(MsgPackrExtension):
    def __init__(self, reader):
        super().__init__(0x70, reader)
        self.set_unpack_handler(self._handler)

    def _handler(self, *args):
        raise NotImplementedError


# Extension 0x73
class Ext115(MsgPackrExtension):
    def __init__(self, reader):
        super().__init__(0x73, reader)
        self.set_unpack_handler(self._handler)

    def _handler(self, *args):
        value = self._reader.read()
        if isinstance(value, collections.abc.Sequence):
            return value
        return []


# Extension 0x74
class Ext116(MsgPackrExtension):
    def __init__(self, reader):
        super().__init__(0x74, reader)
        self.set_unpack_handler(self._handler)

    def _handler(self, *args):
        raise NotImplementedError


# Extension 0x78
class Ext120(MsgPackrExtension):
    def __init__(self, reader):
        super().__init__(0x78, reader)
        self.set_unpack_handler(self._handler)

    def _handler(self, *args):
        raise NotImplementedError


# Extension 0xff
class Ext255(MsgPackrExtension):
    def __init__(self, reader):
        super().__init__(0xFF, reader)
        self.set_unpack_handler(self._handler)

    def _handler(self, *args):
        """
        MessagePack's date/Time specs:

        timestamp 32 stores the number of seconds that have elapsed since 1970-01-01 00:00:00 UTC
        in an 32-bit unsigned integer:
        +--------+--------+--------+--------+--------+--------+
        |  0xd6  |   -1   |   seconds in 32-bit unsigned int  |
        +--------+--------+--------+--------+--------+--------+

        timestamp 64 stores the number of seconds and nanoseconds that have elapsed since 1970-01-01 00:00:00 UTC
        in 32-bit unsigned integers:
        +--------+--------+--------+--------+--------+------|-+--------+--------+--------+--------+
        |  0xd7  |   -1   | nanosec. in 30-bit unsigned int |   seconds in 34-bit unsigned int    |
        +--------+--------+--------+--------+--------+------^-+--------+--------+--------+--------+

        timestamp 96 stores the number of seconds and nanoseconds that have elapsed since 1970-01-01 00:00:00 UTC
        in 64-bit signed integer and 32-bit unsigned integer:
        +--------+--------+--------+--------+--------+--------+--------+
        |  0xc7  |   12   |   -1   |nanoseconds in 32-bit unsigned int |
        +--------+--------+--------+--------+--------+--------+--------+
        +--------+--------+--------+--------+--------+--------+--------+--------+
        |                   seconds in 64-bit signed int                        |
        +--------+--------+--------+--------+--------+--------+--------+--------+
        """
        bytes = args[0]
        length = len(bytes)
        seconds = 0
        nanoseconds = 0

        if length == 4:
            seconds = struct.unpack("!L", bytes)[0]
            nanoseconds = 0
        elif length == 8:
            data64 = struct.unpack("!Q", bytes)[0]
            seconds = data64 & 0x00000003FFFFFFFF
            nanoseconds = data64 >> 34
        elif length == 12:
            nanoseconds, seconds = struct.unpack("!Iq", bytes)
        else:
            raise Exception("Dates can only be created from 32, 64, or 96-bit buffers")

        dt = datetime.timezone.utc  # Set timezone to UTC

        # return UTC datetime value build from extracted seconds and nanoseconds
        return datetime.datetime.fromtimestamp(0, dt) + datetime.timedelta(
            seconds=seconds, microseconds=nanoseconds // 1000
        )


# endregion
