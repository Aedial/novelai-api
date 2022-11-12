from copy import deepcopy
from enum import Enum, IntEnum
from json import loads
from os import listdir
from os.path import abspath, dirname, exists, join
from random import choice
from typing import Any, Dict, List, NoReturn, Optional, Union


# NOTE: the noqa are there because of Enum, because Enum's type inference sucks
class Order(IntEnum):
    Temperature = 0
    Top_K = 1
    Top_P = 2
    TFS = 3
    Top_A = 4
    Typical_P = 5


NAME_TO_ORDER = {
    "tfs": Order.TFS,
    "temperature": Order.Temperature,
    "top_p": Order.Top_P,
    "top_k": Order.Top_K,
    "top_a": Order.Top_A,
    "typical_p": Order.Typical_P,
}

ORDER_TO_NAME = {
    Order.TFS: "tfs",
    Order.Temperature: "temperature",
    Order.Top_P: "top_p",
    Order.Top_K: "top_k",
    Order.Top_A: "top_a",
    Order.Typical_P: "typical_p",
}


def enum_contains(enum_class: Enum, value) -> bool:
    if not hasattr(enum_class, "enum_member_values"):
        enum_class.enum_member_values = list(e.value for e in enum_class)  # noqa

    values = enum_class.enum_member_values
    assert len(values), f"Empty enum class {enum_class}"

    return value in values


class StrEnum(str, Enum):
    pass


class Model(StrEnum):
    # Calliope = "2.7B"
    Sigurd = "6B-v4"
    Euterpe = "euterpe-v2"
    Krake = "krake-v2"

    Genji = "genji-jp-6b-v2"
    Snek = "genji-python-6b"

    HypeBot = "hypebot"
    Inline = "infillmodel"


class PresetView:
    model: Model
    _official_values: Dict[str, List["Preset"]]

    def __init__(self, model: Model, officials_values: Dict[str, List["Preset"]]):
        self.model = model
        self._officials_values = officials_values

    def __iter__(self):
        return self._officials_values[self.model.value].__iter__()


class _PresetMetaclass(type):
    _officials_values: Dict[str, List["Preset"]]

    def __getitem__(cls, model: Model):
        assert isinstance(model, Model)

        return PresetView(model, cls._officials_values)


class Preset(metaclass=_PresetMetaclass):
    # TODO
    # do_sample                     boolean
    # early_stopping                boolean
    # num_beams                     number
    # pad_token_id                  number
    # bos_token_id                  number
    # eos_token_id                  number
    # no_repeat_ngram_size          number
    # encoder_no_repeat_ngram_size	number
    # num_return_sequences          number
    # max_time                      number
    # num_beam_groups               number
    # get_hidden_states             boolean
    # next_word                     boolean
    # output_nonzero_probs          boolean
    # generate_until_sentence       boolean

    _TYPE_MAPPING = {
        "textGenerationSettingsVersion": int,
        "temperature": (int, float),
        "max_length": int,
        "min_length": int,
        "top_k": int,
        "top_a": (int, float),
        "top_p": (int, float),
        "typical_p": (int, float),
        "tail_free_sampling": (int, float),
        "repetition_penalty": (int, float),
        "repetition_penalty_range": int,
        "repetition_penalty_slope": (int, float),
        "repetition_penalty_frequency": (int, float),
        "repetition_penalty_presence": int,
        "repetition_penalty_whitelist": list,
        "length_penalty": (int, float),
        "diversity_penalty": (int, float),
        "order": list,
        "eos_token_id": int,
        "stop_sequences": list,
    }

    _officials: Dict[str, Dict[str, "Preset"]]
    _officials_values: Dict[str, List["Preset"]]
    _defaults: Dict[str, str]

    _enabled: List[bool]

    _settings: Dict[str, Any]
    name: str
    model: Model

    def __init__(self, name: str, model: Model, settings: Optional[Dict[str, Any]] = None):
        self.name = name
        self.model = model

        self._enabled = [True] * len(Order)

        self._settings = {}
        self.update(settings)

    def __setitem__(self, o: str, v: Any):
        assert o in self._TYPE_MAPPING, f"'{o}' is not a valid setting"
        assert isinstance(
            v, self._TYPE_MAPPING[o]  # noqa
        ), f"Expected type '{self._TYPE_MAPPING[o]}' for {o}, but got type '{type(v)}'"

        if o == "order":
            assert isinstance(v, list), f"Expected type 'List[int|Order] for order, but got type '{type(v)}'"

            for i, e in enumerate(v):
                assert isinstance(
                    e, (int, Order)
                ), f"Expected type 'int' or 'Order for order #{i}, but got type '{type(v[i])}'"

                if isinstance(e, int):
                    v[i] = Order(e)

        self._settings[o] = v

    def __contains__(self, o: str) -> bool:
        return o in self._settings

    def __getitem__(self, o: str) -> Optional[Any]:
        return self._settings.get(o)

    def __repr__(self) -> str:
        model = self.model.value if self.model is not None else "<?>"
        return f"Preset: '{self.name} ({model})'"

    def enable(self, **kwargs) -> "Preset":
        for o in Order:
            name = ORDER_TO_NAME[o]
            enabled = kwargs.pop(name, False)
            self._enabled[o.value] = enabled  # noqa

        assert len(kwargs) == 0, f"Invalid order name: {', '.join(kwargs)}"

        return self

    def to_settings(self) -> Dict[str, Any]:
        settings = deepcopy(self._settings)

        if "textGenerationSettingsVersion" in settings:
            del settings["textGenerationSettingsVersion"]  # not API relevant

        for i, o in enumerate(Order):
            if not self._enabled[i]:
                settings["order"].remove(o)

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
        model = Model(model_name) if enum_contains(Model, model_name) else None  # noqa

        settings = data["parameters"] if "parameters" in data else {}

        order = settings["order"] if "order" in settings else {}
        settings["order"] = list(NAME_TO_ORDER[o["id"]] for o in order)

        # TODO: add support for token banning and bias in preset
        settings.pop("bad_words_ids", None)  # get rid of unsupported option
        settings.pop("logit_bias_exp", None)  # get rid of unsupported option
        settings.pop("logit_bias_groups", None)  # get rid of unsupported option

        c = cls(name, model, settings)

        enabled = {o["id"]: o["enabled"] for o in order}
        c.enable(**enabled)

        return c

    @classmethod
    def from_file(cls, path: str) -> "Preset":
        with open(path, encoding="utf-8") as f:
            data = loads(f.read())

        return cls.from_preset_data(data)

    @classmethod
    def from_official(cls, model: Model, name: Optional[str] = None) -> Union["Preset", None]:
        model_value: str = model.value  # noqa

        if name is None:
            preset = choice(cls._officials_values[model_value])
        else:
            preset = cls._officials[model_value].get(name)

        if preset is not None:
            preset = deepcopy(preset)

        return preset

    @classmethod
    def from_default(cls, model: Model) -> Union["Preset", None]:
        model_value: str = model.value  # noqa

        default = cls._defaults.get(model_value)
        if default is None:
            return None

        preset = cls._officials[model_value].get(default)
        if preset is None:
            return None

        return preset.copy()


def import_officials():
    cls = Preset

    cls._officials_values = {}
    cls._officials = {}
    cls._defaults = {}

    for model in Model:
        model: Model

        path = join(
            dirname(abspath(__file__)),
            "presets",
            f"presets_{model.value.replace('-', '_')}",
        )

        if exists(join(path, "default.txt")):
            with open(join(path, "default.txt"), encoding="utf-8") as f:
                cls._defaults[model.value] = f.read().splitlines()[0]

        officials = {}
        for filename in listdir(path):
            if filename.endswith(".preset"):
                preset = cls.from_file(join(path, filename))
                officials[preset.name] = preset

        cls._officials_values[model.value] = list(officials.values())
        cls._officials[model.value] = officials


if not hasattr(Preset, "_officials"):
    import_officials()
