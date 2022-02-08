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
    pass

class Model(StrEnum):
    Calliope = "2.7B"
    Sigurd = "6B-v4"
    Euterpe = "euterpe-v0"
    # TODO: add Euterpe_v2

    Genji = "genji-jp-6b-v2"
    Snek = "genji-python-6b"

class PresetView:
    model: Model
    _official_values: Dict[str, "Preset"]

    def __init__(self, model: Model, officials_values: Dict[str, "Preset"]):
        self.model = model
        self._officials_values = officials_values

    def __iter__(self):
        return self._officials_values[self.model.value].__iter__()

class _PresetMetaclass(type):
    def __getitem__(cls, model: Model):
        assert type(model) is Model

        return PresetView(model, cls._officials_values)

class Preset(metaclass = _PresetMetaclass):
    _TYPE_MAPPING = {
        "temperature": (int, float), "max_length": int, "min_length": int, "top_k": int,
        "top_p": (int, float), "tail_free_sampling": (int, float), "repetition_penalty": (int, float),
        "repetition_penalty_range": int, "repetition_penalty_slope": (float, int),
        "repetition_penalty_frequency": (int, float), "repetition_penalty_presence": int,
        "order": list, "textGenerationSettingsVersion": int
    }

    _officials: Dict[str, "Preset"]
    _officials_values: List["Preset"]
    _defaults: Dict[str, Dict[str, str]]

    _enable_temperature: bool
    _enable_top_k: bool
    _enable_top_p: bool
    _enable_tfs: bool

    _settings: Dict[str, Any]
    name: str
    model: Model

    def __init__(self, name: str, model: Model, settings: Optional[Dict[str, Any]] = None):
        self.name = name
        self.model = model

        self._enable_temperature = True
        self._enable_top_k = True
        self._enable_top_p = True
        self._enable_tfs = True

        self._settings = {}
        self.update(settings)

    def __setitem__(self, o: str, v: Any):
        assert o in self._TYPE_MAPPING, f"'{o}' is not a valid setting"
        assert isinstance(v, self._TYPE_MAPPING[o]), f"Expected type '{self._TYPE_MAPPING[o]}' for {o}, but got type '{type(v)}'"

        if o == "order":
            assert type(v) is list, f"Expected type 'List[int|Order] for order, but got type '{type(v)}'"
            assert len(v) == 4, f"Expected 4 items in order, but only got {len(v)}: {v}"

            for i in range(len(v)):
                assert isinstance(v[i], (int, Order)), f"Expected type 'int' or 'Order for order #{i}, but got type '{type(v[i])}'"

                if type(v[i]) is int:
                    v[i] = Order(v[i])

        self._settings[o] = v

    def __contains__(self, o: str) -> bool:
        return o in self._settings

    def __getitem__(self, o: str) -> Optional[Any]:
        return self._settings.get(o)

    def __repr__(self) -> str:
        model = self.model.value if self.model is not None else "<?>"
        return f"Preset: '{self.name} ({model})'"

    def enable(self, temperature: Optional[bool] = None, top_k: Optional[bool] = None,
                     top_p: Optional[bool] = None, tfs: Optional[bool] = None) -> "Preset":
        if temperature is not None:     self._enable_temperature    = temperature
        if top_k is not None:           self._enable_top_k          = top_k
        if top_p is not None:           self._enable_top_p          = top_p
        if tfs is not None:             self._enable_tfs            = tfs

        assert type(self._enable_temperature) is bool, f"Expected type bool for temperature, but got type '{type(self._enable_temperature)}'"
        assert type(self._enable_top_k) is bool, f"Expected type bool for top_k, but got type '{type(self._enable_top_k)}'"
        assert type(self._enable_top_p) is bool, f"Expected type bool for top_p, but got type '{type(self._enable_top_p)}'"
        assert type(self._enable_tfs) is bool, f"Expected type bool for tfs, but got type '{type(self._enable_tfs)}'"

        return self

    def to_settings(self) -> Dict[str, Any]:
        settings = deepcopy(self._settings)

        if "textGenerationSettingsVersion" in settings:
            del settings["textGenerationSettingsVersion"]   # not API relevant

        if not self._enable_temperature and "temperature" in settings:
            del settings["temperature"]

        if not self._enable_top_k and "top_k" in settings:
            del settings["top_k"]

        if not self._enable_top_p and "top_p" in settings:
            del settings["top_p"]

        if not self._enable_tfs and "tail_free_sampling" in settings:
            del settings["tail_free_sampling"]

        return settings

    def to_file(self, path: str) -> NoReturn:
        raise NotImplementedError()

    def copy(self) -> "Preset":
        return Preset(self.name, self.model, deepcopy(self._settings))

    def set(self, name: str, value: Any) -> "Preset":
        self[name] = value

        return self

    def update(self, values: Dict[str, Any]) -> "Preset":
        for k, v in values.items():
            self[k] = v

        return self

    @classmethod
    def from_preset_data(cls, data: Dict[str, Any]) -> "Preset":
        name = data["name"] if "name" in data else "<?>"

        model_name = data["model"] if "model" in data else ""
        model = Model(model_name) if enum_contains(Model, model_name) else None

        settings = data["parameters"] if "parameters" in data else {}

        order = settings["order"] if "order" in settings else {}
        if order:
            settings["order"] = list(name_to_order(o["id"]) for o in order)

        # TODO: add support for token banning and bias in preset
        settings.pop("bad_words_ids", None)     # get rid of unsupported option
        settings.pop("logit_bias_exp", None)    # get rid of unsupported option
        settings.pop("logit_bias_groups", None)    # get rid of unsupported option

        c = cls(name, model, settings)

        if order:
            enabled = list(o["id"] for o in order if o["enabled"])

            enable_temperature  = "temperature" in enabled
            enable_top_k        = "top_k" in enabled
            enable_top_p        = "top_p" in enabled
            enable_tfs          = "tfs" in enabled

            c.enable(enable_temperature, enable_top_k, enable_top_p, enable_tfs)

        return c

    @classmethod
    def from_file(cls, path: str) -> "Preset":
        with open(path) as f:
            data = loads(f.read())

        return cls.from_preset_data(data)

    @classmethod
    def from_official(cls, model: Model, name: Optional[str] = None) -> Union["Preset", None]:
        if name is None:
            preset = choice(cls._officials_values[model.value])
        else:
            preset = cls._officials[model.value].get(name)

        if preset is not None:
            preset = preset.copy()

        return preset

    @classmethod
    def from_default(cls, model: Model) -> Union["Preset", None]:
        default = cls._defaults.get(model.value)
        if default is None:
            return None

        preset = cls._officials[model.value].get(default)
        if preset is None:
            return None

        return preset.copy()


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