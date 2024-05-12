"""
Python MessagePack Unpacker v1.10.0

Ported from the msgpackr v1.10.0 unpack.js code found at https://github.com/kriszyp/msgpackr
Original javascript code copyright 2020 Kris Zyp, and released under the MIT license

Ported to Python by Jason L. Walker - 2024 and released under the MIT license

Can roughly use the specification found at https://github.com/msgpack/msgpack/blob/master/spec.md
as a reference.

Note: not all portions of the MessagePack unpacking spec have been implemented yet.
      This should be considered an alpha release. Version number listed was chosen to match
      original version of Javascript library
"""
import math
import struct
from enum import IntEnum

from novelai_api.msgpackr.extensions import (
    Ext0,
    Ext66,
    Ext98,
    Ext101,
    Ext105,
    Ext112,
    Ext115,
    Ext116,
    Ext120,
    Ext255,
    MsgPackrExtension,
)


class UnpackOptions:
    def __init__(self, **opts):
        self.use_records = None
        self.maps_as_objects = None
        self.sequential = None
        self.trusted = None
        self.structures = None
        self.max_shared_structures = None
        self.get_structures = None
        self.int64_as_number = False
        self.int64_as_type = None
        self.use_float32 = self.FLOAT32_OPTIONS.NEVER
        self.bundle_strings = None
        self.more_types = None
        self.structured_clone = None
        self.freeze_data = None

    class FLOAT32_OPTIONS(IntEnum):
        NEVER = 0
        ALWAYS = 1
        DECIMAL_ROUND = 3
        DECIMAL_FIT = 4


class MsgPackerStructure:
    def __init__(self, reader, keys):
        self._reader = reader
        self.read = None
        self.keys = keys
        self.high_byte = None
        self.is_shared = False

    def set_read_handler(self, handler):
        self.read = handler

    def can_read(self):
        return callable(self.read)

    def generic_read_handler(self):
        obj = {}
        for key in self.keys:
            obj[key] = self._reader.read()

        return obj


class MsgPackrUnpack(UnpackOptions):
    # region private classes
    class CurrentStructuresModel(dict):
        def __init__(self):
            super().__init__()
            self.restore_structures = None
            self.shared_length = None
            self.uninitialized = None

    class C1Type:
        name = "MessagePack 0xC1"

    # endregion

    C1 = C1Type()
    mult10 = []

    def __new__(cls, **kwargs):
        mult10 = {}
        for i in range(256):
            val = 45.15 - i * 0.30103
            mult10[i] = str(float(f"1e{math.floor(val)}"))
        return super().__new__(cls)

    def __init__(self, **opts):
        super().__init__(**opts)
        self.src = []
        self.src_end = 0
        self.position = 0
        self.strings = []
        self.current_unpackr = None
        self._current_structures = MsgPackrUnpack.CurrentStructuresModel()
        self.src_string = None
        self.src_string_start = 0
        self.src_string_end = 0
        self.bundled_strings = None
        self.reference_map = None
        self._current_extensions = {}
        self.default_options = UnpackOptions(use_records=False)
        self.sequential_mode = False
        self.inline_object_read_threshold = 2
        self.structures = {}
        self.key_cache = []

        self.add_extension(Ext0)
        self.add_extension(Ext66)
        self.add_extension(Ext98)
        self.add_extension(Ext101)
        self.add_extension(Ext105)
        self.add_extension(Ext112)
        self.add_extension(Ext115)
        self.add_extension(Ext116)
        self.add_extension(Ext120)
        self.add_extension(Ext255)

        # Not the best idea, but:
        for key, value in opts:
            setattr(self, key, value)

    def save_state_callback(self, *args):
        self.clear_source()
        return self.unpack(args[0], args[1])

    def unpack(self, source, opts=None):
        if not isinstance(source, (bytes, bytearray)):
            raise Exception("source must contain a byte array")

        if (self.src is not None) and len(self.src) > 0:
            return self.save_state(self.save_state_callback, source, opts)

        if (opts is not None) and isinstance(opts, UnpackOptions):
            self.src_end = opts.end or len(source)
            self.position = opts.start or 0
        else:
            self.position = 0
            if isinstance(opts, int):
                self.src_end = opts
            else:
                self.src_end = len(source)

        self.string_position = 0
        self.src_string_end = 0
        self.src_string = None
        self.strings = []
        self.bundled_strings = None
        self.src = memoryview(source)

        if self.current_unpackr is None:
            self.current_unpackr = self.default_options
            if len(self._current_structures) > 0:
                self._current_structures.clear()

        if self.structures is not None:
            del self._current_structures
            self._current_structures = MsgPackrUnpack.CurrentStructuresModel()
            for structure in self.structures:
                self._current_structures[structure.key] = structure.value
            return self.checked_read(opts)

        if len(self._current_structures) > 0:
            self._current_structures.clear()

        return self.checked_read(opts)

    def unpack_multiple(self, source, for_each):
        raise NotImplementedError

    def _merge_structures(self, loaded_structures, existing_structures):
        raise NotImplementedError

    def decode(self, source, options):
        raise NotImplementedError

    def restore_structures(self):
        if (
            isinstance(self._current_structures, MsgPackrUnpack.CurrentStructuresModel)
            and self._current_structures.restore_structures is not None
        ):
            for key, value in self._currentStructures.restore_structures:
                self._currentStructures[key] = value

            del self._currentStructures.restore_structures
            self._currentStructures.restore_structures = None

    def checked_read(self, options):
        # try:
        if not (isinstance(self.current_unpackr, UnpackOptions) and self.current_unpackr.trusted is True) and not (
            self.sequential_mode
        ):
            shared_length = self._current_structures.get("shared_length") or 0
            if shared_length < len(self._current_structures):
                raise NotImplementedError

        result = self.read()

        if self.bundled_strings is not None:
            self.position = self.bundled_strings.post_bundle_position
            del self.bundled_strings
            self.bundled_strings = None

        if self.sequential_mode:
            # we only need to restore the structures if there was an error, but if we completed a read,
            # we can clear this out and keep the structures we read
            self._currentStructures.restore_structures = None

        if self.position == self.src_end:
            # finished reading this source, cleanup references
            if (
                self._current_structures.restore_structures is not None
                and len(self._current_structures) > 0
                and callable(self.restore_structures)
            ):
                self.restore_structures()
            self._current_structures.clear()
            self.src = None
            if self.reference_map is not None:
                self.reference_ap is None
        elif self.position > self.src_end:
            # over read
            raise Exception("Unexpected end of MessagePack data")
        elif not self.sequential_mode:
            raise Exception("Data read, but end of buffer not reached")

        # else more to read, but we are reading sequentially, so don't clear source yet

        return result

    # except:
    #    if(
    #       isinstance(self._current_structures, MsgPackrUnpack.CurrentStructuresModel)
    #       and self._current_structures.restore_structures is not None
    #       ):
    #        self.restore_structures()
    #    self.clear_source()

    def read(self):
        token = self.read_byte(self.position)
        self.position += 1

        # print(token)

        if token < 0xA0:
            if token < 0x80:
                if token < 0x40:
                    return token
                else:
                    structure = self._current_structures.get(token or 0)
                    if structure is not None or (
                        self.current_unpackr.get_structures and self.load_structures()[(token or 0) & 0x3F] is not None
                    ):
                        if structure is not None:
                            if not structure.can_read():
                                structure.set_read_handler(self.create_structure_reader(structure, token & 0x3F))
                            return structure.read()
                    else:
                        return token
                raise NotImplementedError(f"Unable to map structure: {token}")
            elif token < 0x90:
                # map
                token -= 0x80
                if self.current_unpackr.maps_as_objects:
                    obj = {}
                    for i in range(token):
                        key = self.read_key()
                        if key == "__proto__":
                            key = "__proto_"
                        obj[key] = self.read()
                    return obj
                else:
                    map = {}
                    for i in range(token):
                        key = self.read()
                        value = self.read()
                        if key or key == 0:
                            map[key] = value
                    return map
            else:
                token -= 0x90
                arry = []
                for i in range(token or 0):
                    # print (f"array index: {i}, token:{token}")
                    arry.append(self.read())
                return arry
        elif token < 0xC0:
            # fixstr
            length = token - 0xA0
            if self.src_string_end >= self.position:
                # return srcString.slice(_offset - srcStringStart, (_offset += length) - srcStringStart);
                raise NotImplementedError
            if self.src_string_end == 0 and self.src_end < 140:
                # for small blocks, avoiding the overhead of the extract call is helpful
                if length < 16:
                    str = self.short_string_in_js(length or 0)
                else:
                    str = self.long_string_in_js(length or 0)
                if str is not None:
                    return str
            return self.read_string_js(length or 0)
        else:
            # print(f"token fallback {token}")
            value = None
            if token == 0xC0:
                return None
            elif token == 0xC1:
                if self.bundled_strings is not None:
                    len = int(self.read() or 0)  # followed by the length of the string in characters (not bytes!)
                    if len > 0:
                        start = self.bundled_strings.position1
                        self.bundled_strings.position1 += len
                        return self.bundled_strings.strings[1][start : self.bundled_strings.position1]
                    else:
                        start = self.bundled_strings.position0
                        self.bundled_strings.position0 -= len
                        return self.bundled_strings.strings[0][start : self.bundled_strings.position0]
                return MsgPackrUnpack.C1  # "never-used", return special object to denote that
            elif token == 0xC2:
                return False
            elif token == 0xC3:
                return True
            elif token == 0xC4:
                # bin 8
                value = self.read_byte(self.position)
                self.position += 1
                if value is None:
                    raise Exception("Unexpected end of buffer")
                return self.read_bin(value)
            elif token == 0xC5:
                # bin 16
                length = self.get_uint_16(self.position)
                self.position += 2
                return self.read_bin(length)
            elif token == 0xC6:
                # bin 32
                length = self.get_uint_32(self.position)
                self.position += 4
                return self.read_bin(length)
            elif token == 0xC7:
                # ext 8
                value = self.read_ext(self.position)
                self.position += 1
                return value
            elif token == 0xC8:
                # ext 16
                length = self.get_uint_16(self.position)
                self.position += 2
                return self.read_ext(length)
            elif token == 0xC9:
                # ext 32
                length = self.get_uint_32(self.position)
                self.position += 4
                return self.read_ext(length)
            elif token == 0xCA:
                raise NotImplementedError
            elif token == 0xCB:
                value = self.get_float_64(self.position)
                self.position += 8
                return value
            elif token == 0xCC:
                value = self.read_byte(self.position)
                self.position += 1
                return value
            elif token == 0xCD:
                value = self.get_uint_16(self.position)
                self.position += 2
                return value
            elif token == 0xCE:
                value = self.get_uint_32(self.position)
                self.position += 4
                return value
            elif token == 0xCF:
                raise NotImplementedError
            elif token == 0xD0:
                value = self.get_int_8(self.position)
                self.position += 1
                return value
            elif token == 0xD1:
                value = self.get_int_16(self.position)
                self.position += 2
                return value
            elif token == 0xD2:
                value = self.get_int_32(self.position)
                self.position += 4
                return value
            elif token == 0xD3:
                raise NotImplementedError
            elif token == 0xD4:
                # fixext 1
                value = self.read_byte(self.position)
                self.position += 1
                if value == 0x72:
                    id = self.read_byte(self.position)
                    self.position += 1
                    return self.record_definition(id)
                else:
                    extension = self._current_extensions.get(value)
                    if extension is not None:
                        if extension.can_read():
                            self.position += 1  # skip filler byte
                            # print(f'Reading Extension {extension.get_type()}')
                            return extension.read(self.read())
                        elif extension.can_unpack():
                            if extension.no_buffer:
                                self.position += 1  # skip filler byte
                                # print(f'Unpacking Extension {extension.get_type()}')
                                return extension.unpack(None)

                            bytes = self.read_bytes(self.position, 2)
                            self.position += 1

                            return extension.unpack(bytes)

                raise NotImplementedError(f"Unknown extension {value}")
            elif token == 0xD5:
                # fixext 2
                token = self.read_byte(self.position)
                if token == 0x72:
                    self.position += 1
                    id = self.read_byte(self.position) & 0x3F
                    self.position += 1
                    high_byte = self.read_byte(self.position)
                    self.position += 1
                    return self.record_definition(id, high_byte)
                else:
                    return self.read_ext(2)
            elif token == 0xD6:
                # fixext 4
                return self.read_ext(4)
            elif token == 0xD7:
                # fixext 8
                return self.read_ext(8)
            elif token == 0xD8:
                # fixext 16
                return self.read_ext(16)
            elif token == 0xD9:
                # str 8
                length = self.read_byte(self.position)
                self.position += 1
                if self.src_string_end >= self.position:
                    raise NotImplementedError
                return self.read_string_js(length)
            elif token == 0xDA:
                # str 16
                length = self.get_uint_16(self.position)
                self.position += 2
                if self.src_string_end >= self.position:
                    raise NotImplementedError
                return self.read_string_js(length)
            elif token == 0xDB:
                # str 32
                length = self.get_uint_32(self.position)
                self.position += 4
                if self.src_string_end >= self.position:
                    raise NotImplementedError
                return self.read_string_js(length)
            elif token == 0xDC:
                # array 16
                length = self.get_uint_16(self.position)
                self.position += 2
                return self.read_array(length)
            elif token == 0xDD:
                # array 32
                length = self.get_uint_32(self.position)
                self.position += 4
                return self.read_array(length)
            elif token == 0xDE:
                # map 16
                length = self.get_uint_16(self.position)
                self.position += 2
                return self.read_map(length)
            elif token == 0xDF:
                # map 32
                length = self.get_uint_32(self.position)
                self.position += 4
                return self.read_map(length)
            else:
                # negative int
                if token >= 0xE0:
                    return token - 0x100
                if token is None:
                    raise Exception("Token out of Range - Unexpected end of MessagePack data")

        raise NotImplementedError(f"Unknown MessagePack token {token}")

    def create_structure_reader(self, structure, first_id=None):
        if structure.high_byte == 0:
            return self.create_second_byte_reader(first_id, structure.generic_read_handler)

        return structure.generic_read_handler

    def create_second_byte_reader(self, firstid, read0):
        raise NotImplementedError

    def load_structures(self):
        raise NotImplementedError

    def read_array(self, length):
        arry = []
        for i in range(length):
            arry.append(self.read())

        if self.current_unpackr.freeze_data:
            # return Object.freeze(array)
            raise NotImplementedError
        return arry

    def is_whole_value(self, value):
        raise NotImplementedError

    def get_json_object(self, value):
        raise NotImplementedError

    def from_char_code(self, data, length=1):
        return bytes(data).decode("utf-8")

    # region String Readers
    def long_string_in_js(self, length):
        raise NotImplementedError

    def short_string_in_js(self, length):
        bytes = self.read_bytes(self.position, length)
        if length < 4:
            if length < 2:
                if length == 0:
                    return ""
                else:
                    self.position += 1
                    if (bytes[0] & 0x80) > 1:
                        self.position -= 1
                        return None
                    return self.from_char_code(bytes, 1)
            else:
                self.position += 2
                if (bytes[0] & 0x80) > 0 or (bytes[1] & 0x80) > 0:
                    self.position -= 2
                    return None
                if length < 3:
                    return self.from_char_code(bytes, 2)
                self.position += 1
                if (bytes[2] & 0x80) > 0:
                    self.position -= 3
                    return None
                return self.from_char_code(bytes, 3)
        else:
            self.position += 4
            if (bytes[0] & 0x80) > 0 or (bytes[1] & 0x80) > 0 or (bytes[2] & 0x80) > 0 or (bytes[3] & 0x80) > 0:
                self.position -= 4
                return None
            if length < 6:
                if length == 4:
                    return self.from_char_code(bytes, 4)
                else:
                    self.position += 1
                    if (bytes[4] & 0x80) > 0:
                        self.position -= 5
                        return None
                    return self.from_char_code(bytes, 5)
            elif length < 8:
                self.position += 2
                if (bytes[4] & 0x80) > 0 or (bytes[5] & 0x80) > 0:
                    self.position -= 6
                    return None
                if length < 7:
                    return self.from_char_code(bytes, 6)
                self.position += 1
                if (bytes[6] & 0x80) > 0:
                    self.position -= 7
                    return None
                return self.from_char_code(bytes, 7)
            else:
                self.position += 4
                if (bytes[4] & 0x80) > 0 or (bytes[5] & 0x80) > 0 or (bytes[6] & 0x80) > 0 or (bytes[7] & 0x80) > 0:
                    self.position -= 8
                    return None
                if length < 10:
                    if length == 8:
                        return self.from_char_code(bytes, 8)
                    else:
                        self.position += 1
                        if (bytes[8] & 0x80) > 0:
                            self.position -= 9
                            return None
                        return self.from_char_code(bytes, 9)
                elif length < 12:
                    self.position += 2
                    if (bytes[8] & 0x80) > 0 or (bytes[9] & 0x80) > 0:
                        self.position -= 10
                        return None
                    if length < 11:
                        return self.from_char_code(bytes, 10)
                    self.position += 1
                    if (bytes[10] & 0x80) > 0:
                        self.position -= 11
                        return None
                    return self.from_char_code(bytes, 11)
                else:
                    self.position += 4
                    if (
                        (bytes[8] & 0x80) > 0
                        or (bytes[9] & 0x80) > 0
                        or (bytes[10] & 0x80) > 0
                        or (bytes[11] & 0x80) > 0
                    ):
                        self.position -= 12
                        return None
                    if length < 14:
                        if length == 12:
                            return self.from_char_code(bytes, 12)
                        else:
                            self.position += 1
                            if (bytes[12] & 0x80) > 0:
                                self.position -= 13
                                return None
                            return self.from_char_code(bytes, 13)
                    else:
                        self.position += 2
                        if (bytes[12] & 0x80) > 0 or (bytes[13] & 0x80) > 0:
                            self.position -= 14
                            return None
                        if length < 15:
                            return self.from_char_code(bytes, 14)
                        self.position += 1
                        if (bytes[14] & 0x80) > 0:
                            self.position -= 15
                            return None
                        return self.from_char_code(bytes, 15)
        return None

    def read_only_js_string(self):
        token = self.read_byte(self.position)
        self.position += 1
        length = 0
        if token < 0xC0:
            # fixstr
            length = token - 0xA0
        else:
            if token == 0xD9:
                length = self.read_byte(self.position)
                self.position += 1
            elif token == 0xDA:
                length = self.get_uint_16(self.position)
                self.position += 2
            elif token == 0xDB:
                length = self.get_uint_32(self.position)
                self.position += 4
            else:
                raise AttributeError("Expected string")

        # print(token)
        return self.read_string_js(length)

    def read_string_js(self, length):
        # print("Reading string. Length:", length)
        if length < 16:
            result = self.short_string_in_js(length)
            if len(result):
                return result
        end = self.position + length
        result = ""
        while self.position < end:
            byte1 = self.read_byte(self.position)

            self.position += 1
            if (byte1 & 0x80) == 0:
                # 1 byte
                result += chr(byte1)
            elif (byte1 & 0xE0) == 0xC0:
                # 2 bytes
                byte2 = self.read_byte(self.position) & 0x3F
                self.position += 1
                result += chr(((byte1 & 0x1F) << 6) | byte2)
            elif (byte1 & 0xF0) == 0xE0:
                # 3 bytes
                byte2 = self.read_byte(self.position) & 0x3F
                byte3 = self.read_byte(self.position + 1) & 0x3F
                self.position += 2
                result += chr(((byte1 & 0x1F) << 12) | (byte2 << 6) | byte3)
            elif (byte1 & 0xF8) == 0xF0:
                # 4 bytes
                byte2 = self.read_byte(self.position) & 0x3F
                byte3 = self.read_byte(self.position + 1) & 0x3F
                byte4 = self.read_byte(self.position + 2) & 0x3F
                unit = ((byte1 & 0x07) << 0x12) | (byte2 << 0x0C) | (byte3 << 0x06) | byte4
                if unit > 0xFFFF:
                    unit -= 0x10000
                    result += chr(((unit >> 10) & 0x3FF) | 0xD800)
                    unit = 0xDC00 | (unit & 0x3FF)
                self.position += 3
                result += chr(unit)
            else:
                result += chr(byte1)
        return result

    # endregion

    # region Emulate Javascript Dataview readers
    def get_int_8(self, offset):
        b = self.read_byte(offset)
        if b >= 128:
            return b - 256
        else:
            return b

    def get_int_16(self, offset):
        return struct.unpack(">h", self.read_bytes(offset, 2))[0]

    def get_int_32(self, offset):
        return struct.unpack(">i", self.read_bytes(offset, 4))[0]

    def get_big_int_64(self, offset):
        return struct.unpack(">q", self.read_bytes(offset, 8))[0]

    def get_uint_16(self, offset):
        return struct.unpack(">H", self.read_bytes(offset, 2))[0]

    def get_uint_32(self, offset):
        return struct.unpack(">I", self.read_bytes(offset, 4))[0]

    def get_big_uint_64(self, offset):
        return struct.unpack(">Q", self.read_bytes(offset, 8))[0]

    def get_float_32(self, offset):
        return struct.unpack(">f", self.read_bytes(offset, 4))[0]

    def get_float_64(self, offset):
        return struct.unpack(">d", self.read_bytes(offset, 8))[0]

    # endregion

    # region Read helpers
    def read_bin(self, offset):
        raise NotImplementedError

    def read_ext(self, length):
        type = self.read_byte(self.position)
        self.position += 1
        extension = self._current_extensions.get(type)
        if isinstance(extension, MsgPackrExtension):
            if extension.can_unpack():
                n = self.position
                self.position += length
                return extension.unpack(self.read_bytes(n, length))

        raise NotImplementedError(f"Extension not implemented: {type}")

    def read_key(self, offset):
        raise NotImplementedError

    def seek(self, offset):
        self.position = offset

    def read_byte(self, offset):
        return (self.src[offset : offset + 1] or [None])[0]

    def read_bytes(self, offset, length=1):
        return self.src[offset : offset + length]

    def read_map(self, length):
        if self.current_unpackr.maps_as_objects:
            obj = {}
            for i in range(length):
                key = self.read_key()
                if key == "__proto__":
                    key = "__proto_"
                value = self.read()
                obj[key] = value
            return obj
        else:
            map = {}
            for i in range(length):
                key = self.read()
                # print (key)
                map[key] = self.read()
                # print (f'{key}: {map[key]}')
            return map

    def map(self, obj):
        raise NotImplementedError

    def read_structure(self, id, structure):
        raise NotImplementedError

    # endregion

    # region Helper methods
    def as_safe_string(self, property):
        raise NotImplementedError

    def record_definition(self, id, high_byte=None):
        # print (f'Generating Struct Definition {id}')
        structure = None
        try:
            # Read headers
            keys = self.read()
            structure = MsgPackerStructure(self, keys)

            # for i in range(len(structure.keys)):
            #    structure[structure.keys[i]] = None
        except Exception:
            raise Exception(f"Unable to map structure: {id}:{structure}")

        first_byte = id
        if high_byte is not None:
            if id < 32:
                id = -(((high_byte or 0) << 5) + id)
            else:
                id = ((high_byte or 0) << 5) + id
                structure.high_byte = high_byte

        existing_structure = self._current_structures.get(id)
        if (existing_structure is not None) and (existing_structure.is_shared or self.sequential_mode):
            if self._current_structures is not None:
                self._current_structures.restore_structures = {}
            self._current_structures.restore_structures[id] = existing_structure

        self._current_structures[id] = structure
        structure.set_read_handler(self.create_structure_reader(structure, first_byte))
        return structure.read()

    # endregion

    def save_state(self, callback, *args):
        saved_src_end = self.src_end
        saved_position = self.position
        saved_src_string_start = self.src_string_start
        saved_src_string_end = self.src_string_end
        saved_src_string = self.src_string
        saved_reference_map = self.reference_map
        saved_bundled_strings = self.bundled_strings
        # TODO: We may need to revisit this if we do more external calls to user code (since it could be slow)

        # we copy the data in case it changes while external data is processed.
        # Note: this could reserve large amounts of memory if the unpacker is reused recursively
        saved_src = self.src.tobytes()
        saved_structures = self._current_structures.copy()
        saved_structures_contents = self._current_structures.copy()
        saved_packr = self.current_unpackr
        saved_sequential_mode = self.sequential_mode

        value = None
        if callable(callback):
            value = callback(*args)

        self.src_end = saved_src_end
        self.position = saved_position
        self.src_string_start = saved_src_string_start
        self.src_string_end = saved_src_string_end
        self.src_string = saved_src_string
        self.reference_map = saved_reference_map
        self.bundled_strings = saved_bundled_strings

        # try to recover some memory
        del self.src

        self.src = memoryview(saved_src)
        self.sequential_mode = saved_sequential_mode
        self._current_structures = saved_structures
        self._current_structures = saved_structures_contents
        self.current_unpackr = saved_packr
        return value

    def clear_source(self):
        self.src = []
        self.reference_map = None
        self._current_structures.clear()

    def add_extension(self, extension):
        ext = extension(self)
        self._current_extensions[ext.get_type()] = ext
