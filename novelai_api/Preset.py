from enum import Enum, IntEnum, EnumMeta
from json import loads
from os import listdir
from os.path import join, abspath, dirname, exists
from copy import deepcopy
from random import choice

from typing import Dict, List, Any, Union, Optional, NoReturn

class Order(IntEnum):
    Temperature = 0
    Top_K       = 1
    Top_P       = 2
    TFS         = 3

def name_to_order(name: str) -> Order:
    mapping = { "tfs": Order.TFS, "temperature": Order.Temperature, "top_p": Order.Top_P, "top_k": Order.Top_K }

    return mapping[name]

def enum_contains(enum_class: EnumMeta.__class__, value) -> bool:
    if not hasattr(enum_class, "_member_values"):
        enum_class._member_values = list(enum_class.__members__.values())
    values = enum_class._member_values

    assert len(values), f"Empty enum class {enum_class}"

    if type(value) is type(values[0].value):
        for item in values:
            if item.value == value:
                return True
    elif type(value) is enum_class:
        return value in values

    return False

class StrEnum(str, Enum):
    """
    def __getitem__(self, i: int) -> "StrEnum":
        return self._objects[i]

    def __iter__(self):
        return (e for e in self.__members__)
    """

class Model(StrEnum):
    Calliope = "2.7B"
    Sigurd = "6B-v4"
    Euterpe = "euterpe-v0"

    Genji = "genji-jp-6b"
    Snek = "genji-python-6b"

class Preset:
    _TYPE_MAPPING = {
        "temperature": float, "max_length": int, "min_length": int, "top_k": int,
        "top_p": float, "tail_free_sampling": float, "repetition_penalty": float,
        "repetition_penalty_range": int, "repetition_penalty_slope": float,
        "repetition_penalty_frequency": int, "repetition_penalty_presence": int,
        "order": list
    }

    _officials: Dict[str, "Preset"]
    _defaults: Dict[str, Dict[str, str]]

    _settings: Dict[str, Any]
    name: str
    model: Model

    def __init__(self, name: str, model: Model, settings: Optional[Dict[str, Any]] = None):
        self.name = name
        self.model = model

        self._settings = {} if settings is None else settings

    def __setitem__(self, o: str, v: Any):
        assert o in self._TYPE_MAPPING, f"'{o}' is not a valid setting"
        assert isinstance(v, self._TYPE_MAPPING[o]), f"Expected type '{self._TYPE_MAPPING[o]}' for {o}, but got type '{type(v)}'"

        if o == "order":
            for i in range(len(v)):
                assert isinstance(v[i], (int, Order)), f"Expected type 'int' or 'Order for order #{i}, but got type '{type(v[i])}'"

                if type(v[i]) is int:
                    v[i] = Order(v[i])

        self._settings[o] = v

    def __contains__(self, o: str) -> bool:
        return o in self._settings

    def __getitem__(self, o: str) -> Any:
        return self._settings.get(o)

    def to_settings(self) -> Dict[str, Any]:
        return deepcopy(self._settings)

    def to_file(self, path: str) -> NoReturn:
        raise NotImplementedError()

    def copy(self) -> "Preset":
        return Preset(self.name, self.model, deepcopy(self._settings))

    def set(self, name: str, value: Any) -> "Preset":
        self[name] = value

        return self

    @classmethod
    def from_file(cls, path: str) -> "Preset":
        with open(path) as f:
            data = loads(f.read())

        name = data["name"] if "name" in data else ""

        model_name = data["model"] if "model" in data else ""
        model = Model(model_name) if enum_contains(Model, model_name) else None

        settings = data["parameters"] if "parameters" in data else None
        if "textGenerationSettingsVersion" in settings:
            del settings["textGenerationSettingsVersion"]   # not API relevant

        if settings and "order" in settings:
            settings["order"] = list(name_to_order(o["id"]) for o in settings["order"] if o["enabled"])

        return cls(name, model, settings)

    @classmethod
    def from_official(cls, model: Model, name: Optional[str] = None) -> Union["Preset", None]:
        if name is None:
            return choice(cls._officials_values[model.value])

        return cls._officials[model.value].get(name)

    @classmethod
    def from_default(cls, model: Model) -> Union["Preset", None]:
        default = cls._defaults.get(model.value)
        if default is None:
            return None

        return cls._officials[model.value].get(default)


if not hasattr(Preset, "_officials"):
    cls = Preset

    cls._officials_values = {}
    cls._officials = {}
    cls._defaults = {}

    for model in Model:
        path = join(dirname(abspath(__file__)), "presets", f"presets_{model.value.replace('-', '_')}")

        if exists(join(path, "default.txt")):
            with open(join(path, "default.txt")) as f:
                cls._defaults[model.value] = f.read()

        officials = {}
        for filename in listdir(path):
            if filename.endswith(".preset"):
                preset = cls.from_file(join(path, filename))
                officials[preset.name] = preset

        cls._officials_values[model.value] = list(officials.values())
        cls._officials[model.value] = officials