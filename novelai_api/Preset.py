import os
import pathlib
import warnings
from copy import deepcopy
from enum import Enum, EnumMeta, IntEnum
from json import loads
from random import choice
from typing import TYPE_CHECKING, Any, Dict, List, NoReturn, Optional, Union


class Order(IntEnum):
    Temperature = 0
    Top_K = 1
    Top_P = 2
    TFS = 3
    Top_A = 4
    Typical_P = 5


NAME_TO_ORDER = {
    "temperature": Order.Temperature,
    "top_k": Order.Top_K,
    "top_p": Order.Top_P,
    "tfs": Order.TFS,
    "top_a": Order.Top_A,
    "typical_p": Order.Typical_P,
}

ORDER_TO_NAME = {
    Order.Temperature: "temperature",
    Order.Top_K: "top_k",
    Order.Top_P: "top_p",
    Order.TFS: "tfs",
    Order.Top_A: "top_a",
    Order.Typical_P: "typical_p",
}


def enum_contains(enum_class: EnumMeta, value: str) -> bool:
    """
    Check if the value provided is valid for the enum

    :param enum_class: Class of the Enum
    :param value: Value to check
    """

    if not hasattr(enum_class, "enum_member_values"):
        enum_class.enum_member_values = list(e.value for e in enum_class)

    values = enum_class.enum_member_values
    if len(values) == 0:
        raise ValueError(f"Empty enum class: '{enum_class}'")

    return value in values


def _strip_model_version(value: str) -> str:
    parts = value.split("-")

    if parts[-1].startswith("v") and parts[-1][1:].isdecimal():
        parts = parts[:-1]

    return "-".join(parts)


def collapse_model(enum_class: EnumMeta, value: str):
    """
    Collapse multiple version of a model to the last model value

    :param enum_class: Class of the Enum
    :param value: Value of the model to collapse
    """

    if not hasattr(enum_class, "enum_member_values"):
        enum_class.enum_member_values = {_strip_model_version(e.value): e for e in enum_class}

    values = enum_class.enum_member_values
    if len(values) == 0:
        raise ValueError(f"Empty enum class: '{enum_class}'")

    return values.get(_strip_model_version(value))


class StrEnum(str, Enum):
    pass


class Model(StrEnum):
    # Calliope = "2.7B"
    Sigurd = "6B-v4"
    Euterpe = "euterpe-v2"
    Krake = "krake-v2"

    Clio = "clio-v1"

    Genji = "genji-jp-6b-v2"
    Snek = "genji-python-6b"

    HypeBot = "hypebot"
    Inline = "infillmodel"


PREAMBLE = {
    Model.Sigurd: "⁂\n",
    Model.Euterpe: "\n***\n",
    Model.Krake: "<|endoftext|>[ Prologue ]\n",
}


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
        if not isinstance(model, Model):
            raise ValueError(f"Expected instance of {type(Model)}, got type '{type(model)}'")

        return PresetView(model, cls._officials_values)


class Preset(metaclass=_PresetMetaclass):
    # TODO
    # no_repeat_ngram_size          number
    # encoder_no_repeat_ngram_size	number
    # num_return_sequences          number
    # get_hidden_states             boolean
    # next_word                     boolean
    # output_nonzero_probs          boolean

    _TYPE_MAPPING = {
        "textGenerationSettingsVersion": int,
        "stop_sequences": list,
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
        "repetition_penalty_presence": (int, float),
        "repetition_penalty_whitelist": list,
        "length_penalty": (int, float),
        "diversity_penalty": (int, float),
        "order": list,
        "pad_token_id": int,
        "bos_token_id": int,
        "eos_token_id": int,
        "max_time": int,
    }

    DEFAULTS = {
        "stop_sequences": [],
        "temperature": 1.0,
        "max_length": 40,
        "min_length": 1,
        "top_k": 0,
        "top_a": 1.0,
        "top_p": 0.0,
        "typical_p": 0.0,
        "tail_free_sampling": 1.0,
        "repetition_penalty": 1.0,
        "repetition_penalty_range": 0,
        "repetition_penalty_slope": 0.0,
        "repetition_penalty_frequency": 0.0,
        "repetition_penalty_presence": 0.0,
        "repetition_penalty_whitelist": [],
        "length_penalty": 1.0,
        "diversity_penalty": 0.0,
        "order": list(Order),
    }

    # type completion for __setitem__ and __getitem__
    if TYPE_CHECKING:
        #: Preset version, only relevant for .preset files
        textGenerationSettingsVersion: int
        #: List of tokenized strings that should stop the generation early
        # TODO: add possibility for late tokenization
        stop_sequences: List[List[int]]
        #: https://naidb.miraheze.org/wiki/Generation_Settings#Randomness_(Temperature)
        temperature: float
        #: Response length, if no interrupted by a Stop Sequence
        max_length: int
        #: Minimum number of token, if interrupted by a Stop Sequence
        min_length: int
        #: https://naidb.miraheze.org/wiki/Generation_Settings#Top-K_Sampling
        top_k: int
        #: https://naidb.miraheze.org/wiki/Generation_Settings#Top-A_Sampling
        top_a: float
        #: https://naidb.miraheze.org/wiki/Generation_Settings#Nucleus_Sampling
        top_p: float
        #: https://naidb.miraheze.org/wiki/Generation_Settings#Typical_Sampling (https://arxiv.org/pdf/2202.00666.pdf)
        typical_p: float
        #: https://naidb.miraheze.org/wiki/Generation_Settings#Tail-Free_Sampling
        tail_free_sampling: float
        #: https://arxiv.org/pdf/1909.05858.pdf
        repetition_penalty: float
        #: Range (in tokens) the repetition penalty covers (https://arxiv.org/pdf/1909.05858.pdf)
        repetition_penalty_range: int
        #: https://arxiv.org/pdf/1909.05858.pdf
        repetition_penalty_slope: float
        #: https://platform.openai.com/docs/api-reference/parameter-details
        repetition_penalty_frequency: float
        #: https://platform.openai.com/docs/api-reference/parameter-details
        repetition_penalty_presence: float
        #: List of tokens that are excluded from the repetition penalty (useful for colors and the likes)
        repetition_penalty_whitelist: list
        #: https://huggingface.co/docs/transformers/main_classes/text_generation#transformers.GenerationConfig
        length_penalty: float
        #: https://huggingface.co/docs/transformers/main_classes/text_generation#transformers.GenerationConfig
        diversity_penalty: float
        #: list of Order to set the sampling order
        order: List[Union[Order, int]]
        #: https://huggingface.co/docs/transformers/main_classes/text_generation#transformers.GenerationConfig
        pad_token_id: int
        #: https://huggingface.co/docs/transformers/main_classes/text_generation#transformers.GenerationConfig
        bos_token_id: int
        #: https://huggingface.co/docs/transformers/main_classes/text_generation#transformers.GenerationConfig
        eos_token_id: int
        #: https://huggingface.co/docs/transformers/main_classes/text_generation#transformers.GenerationConfig
        max_time: int

    _officials: Dict[str, Dict[str, "Preset"]]
    _officials_values: Dict[str, List["Preset"]]
    _defaults: Dict[str, str]

    _enabled: List[bool]

    _settings: Dict[str, Any]

    #: Name of the preset
    name: str
    #: Model the preset is for
    model: Model

    def __init__(self, name: str, model: Model, settings: Optional[Dict[str, Any]] = None):
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "model", model)

        object.__setattr__(self, "_enabled", [True] * len(Order))

        object.__setattr__(self, "_settings", {})
        self.update(settings)

    def __setitem__(self, key: str, value: Any):
        if key not in self._TYPE_MAPPING:
            raise ValueError(f"'{key}' is not a valid setting")

        if not isinstance(value, self._TYPE_MAPPING[key]):  # noqa (pycharm PY-36317)
            raise ValueError(f"Expected type '{self._TYPE_MAPPING[key]}' for {key}, but got type '{type(value)}'")

        self._settings[key] = value

        if key == "order":
            if not isinstance(value, list):
                raise ValueError(f"Expected type 'List[int|Order] for order, but got type '{type(value)}'")

            for i, e in enumerate(value):
                if not isinstance(e, (int, Order)):
                    raise ValueError(f"Expected type 'int' or 'Order for order #{i}, but got type '{type(value[i])}'")

                if isinstance(e, int):
                    value[i] = Order(e)

        self._settings[key] = value

    def __contains__(self, key: str) -> bool:
        return key in self._settings

    def __getitem__(self, key: str) -> Optional[Any]:
        return self._settings.get(key)

    def __delitem__(self, key):
        del self._settings[key]

    # give dot access capabilities to the object
    def __setattr__(self, key, value):
        if key in self._TYPE_MAPPING:
            self[key] = value
        else:
            object.__setattr__(self, key, value)

    def __getattr__(self, key):
        if key in self._TYPE_MAPPING:
            return self[key]

        return object.__getattribute__(self, key)

    def __delattr__(self, name):
        if name in self._TYPE_MAPPING:
            del self[name]
        else:
            object.__delattr__(self, name)

    def __repr__(self) -> str:
        model = self.model.value if self.model is not None else "<?>"
        enabled_keys = ", ".join(f"{k} = {v}" for k, v in zip(self._enabled, NAME_TO_ORDER.keys()))

        return f"Preset: '{self.name} ({model}, {enabled_keys})'"

    def enable(self, **kwargs) -> "Preset":
        """
        Enable/disable the processing of sampling values (True to enable, False to disable).

        The allowed keys are :
            * tfs
            * temperature
            * top_p
            * top_k
            * top_a
            * typical_p
        """

        for o in Order:
            name = ORDER_TO_NAME[o]
            enabled = kwargs.pop(name, None)
            if enabled is not None:
                self._enabled[o.value] = enabled

        if len(kwargs):
            raise ValueError(f"Invalid order name: {', '.join(kwargs)}")

        return self

    def to_settings(self) -> Dict[str, Any]:
        """
        Return the values stored in the preset, for a generate function
        """

        settings = deepcopy(self._settings)

        if "textGenerationSettingsVersion" in settings:
            del settings["textGenerationSettingsVersion"]  # not API relevant

        # remove disabled sampling options
        if "order" in settings:
            for i, o in enumerate(Order):
                if not self._enabled[i]:
                    settings["order"].remove(o)
                    settings.pop(ORDER_TO_NAME[o], None)

            settings["order"] = [e.value for e in settings["order"]]

        # seems that 0 doesn't disable it, but does weird things
        if settings.get("repetition_penalty_range", None) == 0:
            del settings["repetition_penalty_range"]

        # delete the options that return an unknown error (success status code, but server error)
        if settings.get("repetition_penalty_slope", None) == 0:
            del settings["repetition_penalty_slope"]

        return settings

    def __str__(self):
        settings = {k: self._settings.get(k, v) for k, v in self.DEFAULTS.items()}
        is_default = {k: " (default)" if v == self.DEFAULTS[k] else "" for k, v in settings.items()}

        values = "\n".join(f"    {k} = {v}{is_default[k]}" for k, v in settings.items())

        return f"Preset<{self.name}, {self.model}> {{\n{values}\n}}"

    def to_file(self, path: str) -> NoReturn:
        """
        Write the current preset to a file

        :param path: Path to the preset file to write
        """

        raise NotImplementedError()

    def copy(self) -> "Preset":
        """
        Instantiate a new preset object from the current one
        """

        return Preset(self.name, self.model, deepcopy(self._settings))

    def set(self, name: str, value: Any) -> "Preset":
        """
        Set a preset value. Same as `preset[name] = value`
        """

        self[name] = value

        return self

    def update(self, values: Optional[Dict[str, Any]] = None, **kwargs) -> "Preset":
        """
        Update the settings stored in the preset. Works like dict.update()
        """

        if values is not None:
            for k, v in values.items():
                self[k] = v

        for k, v in kwargs.items():
            self[k] = v

        return self

    @classmethod
    def from_preset_data(cls, data: Optional[Dict[str, Any]] = None, **kwargs) -> "Preset":
        """
        Instantiate a preset from preset data, the data should be the same as in a preset file.
        Works like dict.update()
        """

        if data is None:
            data = {}
        data.update(kwargs)

        name = data["name"] if "name" in data else "<?>"

        # FIXME: collapse model version
        model_name = data["model"] if "model" in data else ""
        model = collapse_model(Model, model_name)

        settings = data["parameters"] if "parameters" in data else {}

        order = settings["order"] if "order" in settings else []
        settings["order"] = [NAME_TO_ORDER[o["id"]] for o in order]

        # TODO: add support for token banning and bias in preset
        settings.pop("bad_words_ids", None)  # get rid of unsupported option
        settings.pop("logit_bias_exp", None)  # get rid of unsupported option
        settings.pop("logit_bias_groups", None)  # get rid of unsupported option

        c = cls(name, model, settings)

        enabled = {o["id"]: o["enabled"] for o in order}
        c.enable(**enabled)

        return c

    @classmethod
    def from_file(cls, path: Union[str, bytes, os.PathLike[str], os.PathLike[bytes], int]) -> "Preset":
        """
        Instantiate a preset from the given file

        :param path: Path to the preset file
        """

        with open(path, encoding="utf-8") as f:
            data = loads(f.read())

        return cls.from_preset_data(data)

    @classmethod
    def from_official(cls, model: Model, name: Optional[str] = None) -> Union["Preset", None]:
        """
        Return a copy of an official preset

        :param model: Model to get the preset of
        :param name: Name of the preset. None means a random official preset should be returned

        :return: The chosen preset, or None if the name was not found in the list of official presets
        """

        model_value: str = model.value

        if name is None:
            preset = choice(cls._officials_values[model_value])
        else:
            preset = cls._officials[model_value].get(name)

        if preset is not None:
            preset = deepcopy(preset)

        return preset

    @classmethod
    def from_default(cls, model: Model) -> Union["Preset", None]:
        """
        Return a copy of the default preset for the given model

        :param model: Model to get the default preset of

        :return: The chosen preset, or None if the default preset was not found for the model
        """

        model_value: str = model.value

        default = cls._defaults.get(model_value)
        if default is None:
            return None

        preset = cls._officials[model_value].get(default)
        if preset is not None:
            preset = deepcopy(preset)

        return preset


def _import_officials():
    """
    Import the official presets under the 'presets' directory. Performed once, at import
    """

    cls = Preset

    cls._officials_values = {}
    cls._officials = {}
    cls._defaults = {}

    for model in Model:
        model: Model

        path = pathlib.Path(__file__).parent / "presets" / f"presets_{model.value.replace('-', '_')}"
        if not path.exists():
            warnings.warn(f"Missing preset folder for model {model.value}")
            cls._officials_values[model.value] = []
            cls._officials[model.value] = {}
            continue

        if (path / "default.txt").exists():
            with open(path / "default.txt", encoding="utf-8") as f:
                cls._defaults[model.value] = f.read().splitlines()[0]

        officials = {}
        for filename in path.iterdir():
            if filename.suffix == ".preset":
                preset = cls.from_file(str(path / filename))
                officials[preset.name] = preset

        cls._officials_values[model.value] = list(officials.values())
        cls._officials[model.value] = officials


if not hasattr(Preset, "_officials"):
    _import_officials()
