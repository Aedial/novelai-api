import copy
import enum
import json
import math
import os
import random
import sys
import typing
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from novelai_api.ImagePreset_CostTables import DDIM_COSTS, NAI_COSTS, SMEA_COSTS, SMEA_DYN_COSTS
from novelai_api.python_utils import NoneType, expand_kwargs


class ImageModel(enum.Enum):
    """
    Image model for low_level.suggest_tags() and low_level.generate_image()
    """

    Anime_Curated = "safe-diffusion"
    Anime_Full = "nai-diffusion"
    Furry = "nai-diffusion-furry"

    Inpainting_Anime_Curated = "safe-diffusion-inpainting"
    Inpainting_Anime_Full = "nai-diffusion-inpainting"
    Inpainting_Furry = "furry-diffusion-inpainting"

    Anime_v2 = "nai-diffusion-2"

    Anime_v3 = "nai-diffusion-3"
    Inpainting_Anime_v3 = "nai-diffusion-3-inpainting"


class ControlNetModel(enum.Enum):
    """
    ControlNet Model for ImagePreset.controlnet_model and low_level.generate_controlnet_mask()
    """

    Palette_Swap = "hed"
    Form_Lock = "midas"
    Scribbler = "fake_scribble"
    Building_Control = "mlsd"
    Landscaper = "uniformer"


class ImageResolution(enum.Enum):
    """
    Image resolution for ImagePreset.resolution
    """

    Wallpaper_Portrait = (1088, 1920)
    Wallpaper_Landscape = (1920, 1088)

    # v1
    Small_Portrait = (384, 640)
    Small_Landscape = (640, 384)
    Small_Square = (512, 512)

    Normal_Portrait = (512, 768)
    Normal_Landscape = (768, 512)
    Normal_Square = (640, 640)

    Large_Portrait = (512, 1024)
    Large_Landscape = (1024, 512)
    Large_Square = (1024, 1024)

    # v2
    Small_Portrait_v2 = (512, 768)
    Small_Landscape_v2 = (768, 512)
    Small_Square_v2 = (640, 640)

    Normal_Portrait_v2 = (832, 1216)
    Normal_Landscape_v2 = (1216, 832)
    Normal_Square_v2 = (1024, 1024)

    Large_Portrait_v2 = (1024, 1536)
    Large_Landscape_v2 = (1536, 1024)
    Large_Square_v2 = (1472, 1472)

    # v3
    Small_Portrait_v3 = (512, 768)
    Small_Landscape_v3 = (768, 512)
    Small_Square_v3 = (640, 640)

    Normal_Portrait_v3 = (832, 1216)
    Normal_Landscape_v3 = (1216, 832)
    Normal_Square_v3 = (1024, 1024)

    Large_Portrait_v3 = (1024, 1536)
    Large_Landscape_v3 = (1536, 1024)
    Large_Square_v3 = (1472, 1472)


class ImageSampler(enum.Enum):
    """
    Sampler for ImagePreset.sampler
    """

    k_lms = "k_lms"
    k_euler = "k_euler"
    k_euler_ancestral = "k_euler_ancestral"
    k_heun = "k_heun"
    plms = "plms"  # doesn't work
    ddim = "ddim"
    ddim_v3 = "ddim_v3"  # for v3

    nai_smea = "nai_smea"  # doesn't work
    nai_smea_dyn = "nai_smea_dyn"

    k_dpmpp_2m = "k_dpmpp_2m"
    k_dpmpp_2s_ancestral = "k_dpmpp_2s_ancestral"
    k_dpmpp_sde = "k_dpmpp_sde"
    k_dpm_2 = "k_dpm_2"
    k_dpm_2_ancestral = "k_dpm_2_ancestral"
    k_dpm_adaptive = "k_dpm_adaptive"
    k_dpm_fast = "k_dpm_fast"


class UCPreset(enum.Enum):
    """
    Default UC preset for ImagePreset.uc_preset
    """

    Preset_Low_Quality_Bad_Anatomy = 0
    Preset_Low_Quality = 1
    Preset_Bad_Anatomy = 2
    Preset_None = 3

    Preset_Heavy = 4
    Preset_Light = 5


class ImageGenerationType(enum.Enum):
    """
    Image generation type for low_level.generate_image
    """

    NORMAL = "generate"
    IMG2IMG = "img2img"
    INPAINTING = "infill"


class ImagePreset:
    _UC_Presets = {
        # v1
        ImageModel.Anime_Curated: {
            UCPreset.Preset_Low_Quality_Bad_Anatomy: "nsfw, lowres, bad anatomy, bad hands, text, error, "
            "missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, "
            "jpeg artifacts, signature, watermark, username, blurry",
            UCPreset.Preset_Bad_Anatomy: None,
            UCPreset.Preset_Low_Quality: "nsfw, lowres, text, cropped, worst quality, low quality, normal quality, "
            "jpeg artifacts, signature, watermark, twitter username, blurry",
            UCPreset.Preset_None: "lowres",
        },
        ImageModel.Anime_Full: {
            UCPreset.Preset_Low_Quality_Bad_Anatomy: "nsfw, lowres, bad anatomy, bad hands, text, error, "
            "missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, "
            "jpeg artifacts, signature, watermark, username, blurry",
            UCPreset.Preset_Bad_Anatomy: None,
            UCPreset.Preset_Low_Quality: "nsfw, lowres, text, cropped, worst quality, low quality, normal quality, "
            "jpeg artifacts, signature, watermark, twitter username, blurry",
            UCPreset.Preset_None: "lowres",
        },
        ImageModel.Furry: {
            UCPreset.Preset_Low_Quality_Bad_Anatomy: None,
            UCPreset.Preset_Low_Quality: "nsfw, worst quality, low quality, what has science done, what, "
            "nightmare fuel, eldritch horror, where is your god now, why",
            UCPreset.Preset_Bad_Anatomy: "{worst quality}, low quality, distracting watermark, [nightmare fuel], "
            "{{unfinished}}, deformed, outline, pattern, simple background",
            UCPreset.Preset_None: "low res",
        },
        # v2
        ImageModel.Anime_v2: {
            UCPreset.Preset_Heavy: "nsfw, lowres, bad, text, error, missing, extra, fewer, cropped, jpeg artifacts, "
            "worst quality, bad quality, watermark, displeasing, unfinished, chromatic aberration, scan, "
            "scan artifacts",
            UCPreset.Preset_Light: "nsfw, lowres, jpeg artifacts, worst quality, watermark, blurry, very displeasing",
            UCPreset.Preset_None: "lowres",
        },
        # v3
        ImageModel.Anime_v3: {
            UCPreset.Preset_Heavy: "nsfw, lowres, {bad}, error, fewer, extra, missing, worst quality, jpeg artifacts, "
            "bad quality, watermark, unfinished, displeasing, chromatic aberration, signature, extra digits, "
            "artistic error, username, scan, [abstract]",
            UCPreset.Preset_Light: "nsfw, lowres, jpeg artifacts, worst quality, watermark, blurry, very displeasing",
            UCPreset.Preset_None: "lowres",
        },
    }

    # inpainting presets are the same as the normal ones
    _UC_Presets[ImageModel.Inpainting_Anime_Curated] = _UC_Presets[ImageModel.Anime_Curated]
    _UC_Presets[ImageModel.Inpainting_Anime_Full] = _UC_Presets[ImageModel.Anime_Full]
    _UC_Presets[ImageModel.Inpainting_Furry] = _UC_Presets[ImageModel.Furry]
    _UC_Presets[ImageModel.Inpainting_Anime_v3] = _UC_Presets[ImageModel.Anime_v3]

    _CONTROLNET_MODELS = {
        ControlNetModel.Palette_Swap: "hed",
        ControlNetModel.Form_Lock: "depth",
        ControlNetModel.Scribbler: "scribble",
        ControlNetModel.Building_Control: "mlsd",
        ControlNetModel.Landscaper: "seg",
    }

    _TYPE_MAPPING = {
        "legacy": bool,
        # rest is populated in at the bottom of the file
    }

    # type completion for __setitem__ and __getitem__
    #: https://docs.novelai.net/image/qualitytags.html
    quality_toggle: bool
    #: Automatically uses SMEA when image is above 1 megapixel
    auto_smea: bool
    #: Resolution of the image to generate as ImageResolution or a (width, height) tuple
    resolution: Union[ImageResolution, Tuple[int, int]]
    #: Default UC to prepend to the UC
    uc_preset: Union[UCPreset, None]
    #: Number of images to return
    n_samples: int
    #: Random seed to use for the image. The ith image has seed + i for seed
    seed: int
    #: https://docs.novelai.net/image/sampling.html
    sampler: ImageSampler
    #: https://docs.novelai.net/image/strengthnoise.html
    noise: float
    #: https://docs.novelai.net/image/strengthnoise.html
    strength: float
    #: https://docs.novelai.net/image/stepsguidance.html (scale is called Prompt Guidance)
    scale: float
    #: TODO
    uncond_scale: float
    #: https://docs.novelai.net/image/stepsguidance.html
    steps: int
    #: https://docs.novelai.net/image/undesiredcontent.html
    uc: str
    #: Enable SMEA for any sampler (makes Large+ generations manageable)
    smea: bool
    #: Enable SMEA DYN for any sampler if SMEA is enabled (best for Large+, but not Wallpaper resolutions)
    smea_dyn: bool
    #: b64-encoded png image for img2img
    image: str
    #: Controlnet mask gotten by the generate_controlnet_mask method
    controlnet_condition: str
    #: Model to use for the controlnet
    controlnet_model: ControlNetModel
    #: Influence of the chosen controlnet on the image
    controlnet_strength: float
    #: Reduce the deepfrying effects of high scale (https://twitter.com/Birchlabs/status/1582165379832348672)
    decrisper: bool
    #: Prevent seams along the edges of the mask, but may change the image slightly
    add_original_image: bool
    #: Mask for inpainting (b64-encoded black and white png image, white is the inpainting area)
    mask: str
    #: https://docs.novelai.net/image/stepsguidance.html#prompt-guidance-rescale
    cfg_rescale: float
    #: ??? (TODO: use an enum ? - valid values: native, karras, exponential, polyexponential)
    noise_schedule: str
    #: b64-encoded png image for Vibe Transfer
    reference_image: str
    #: https://docs.novelai.net/.image/vibetransfer.html#information-extracted
    reference_information_extracted: float
    #: https://docs.novelai.net/.image/vibetransfer.html#reference-strength
    reference_strength: float
    #: reference_image for multi-vibe transfer
    reference_image_multiple: List[str]
    #: reference_information_extracted for multi-vibe transfer
    reference_information_extracted_multiple: List[float]
    #: reference_strength for multi-vibe transfer
    reference_strength_multiple: List[float]

    #: Use the old behavior of prompt separation at the 75 tokens mark (can cut words in half)
    legacy_v3_extend: bool
    #: ???
    params_version: int

    _settings: Dict[str, Any]

    #: Seed provided when generating an image with seed 0 (default). Seed is also in metadata, but might be a hassle
    last_seed: int

    @classmethod
    def from_file(cls, path: Union[str, bytes, os.PathLike, int]) -> "ImagePreset":
        """
        Write the preset to a file

        :param path: Path to the file to read the preset from
        """

        with open(path, encoding="utf-8") as f:
            data = json.loads(f.read())

        return cls(**data)

    def to_file(self, path: Union[str, bytes, os.PathLike, int]):
        """
        Load the preset from a file

        :param path: Path to the file to write the preset to
        """

        with open(path, "w", encoding="utf-8") as f:
            f.write(json.dumps(self._settings))

    @expand_kwargs(_TYPE_MAPPING.keys(), _TYPE_MAPPING.values())
    def __init__(self, **kwargs):
        """
        Create an empty ImagePreset. Use the "from_*_config" functions to create a
        """

        object.__setattr__(self, "_settings", {})
        self.update(kwargs)

        object.__setattr__(self, "last_seed", 0)

    @classmethod
    def from_v1_config(cls):
        """
        Create a new ImagePreset with the default settings from the v1 config
        """

        return cls.from_file(Path(__file__).parent / "image_presets" / "presets_v1" / "default.preset")

    @classmethod
    def from_v2_config(cls):
        """
        Create a new ImagePreset with the default settings from the v2 config
        """

        return cls.from_file(Path(__file__).parent / "image_presets" / "presets_v2" / "default.preset")

    @classmethod
    def from_v3_config(cls):
        """
        Create a new ImagePreset with the default settings from the v3 config
        """

        return cls.from_file(Path(__file__).parent / "image_presets" / "presets_v3" / "default.preset")

    @classmethod
    def from_default_config(cls, model: ImageModel) -> "ImagePreset":
        """
        Create a new ImagePreset with the default settings inferring the version from the model

        :param model: Model to use
        """

        if model in (
            ImageModel.Anime_Curated,
            ImageModel.Anime_Full,
            ImageModel.Furry,
            ImageModel.Inpainting_Anime_Curated,
            ImageModel.Inpainting_Anime_Full,
            ImageModel.Inpainting_Furry,
        ):
            return cls.from_v1_config()
        elif model in (ImageModel.Anime_v2,):
            return cls.from_v2_config()
        elif model in (ImageModel.Anime_v3, ImageModel.Inpainting_Anime_v3):
            return cls.from_v3_config()

    def __setitem__(self, key: str, value: Any):
        if key not in self._TYPE_MAPPING:
            raise ValueError(f"'{key}' is not a valid setting")

        # try to cast into enum if possible
        types = self._TYPE_MAPPING[key]
        if not isinstance(types, tuple):
            types = (types,)

        enum_types = [t for t in types if t.__class__ is enum.EnumMeta]
        if enum_types and isinstance(value, str):
            for enum_type in enum_types:
                if value in enum_type.__members__:  # noqa
                    value = enum_type[value]  # noqa
                    break

        if not isinstance(value, self._TYPE_MAPPING[key]):  # noqa (pycharm PY-36317)
            raise ValueError(f"Expected type '{self._TYPE_MAPPING[key]}' for {key}, but got type '{type(value)}'")

        self._settings[key] = value

    def __getitem__(self, key: str):
        return self._settings[key]

    def __delitem__(self, key):
        if key in self._DEFAULT:
            raise ValueError(f"'{key}' is a default setting, set it instead of deleting")

        del self._settings[key]

    def __contains__(self, key: str):
        return key in self._settings.keys()

    def update(self, values: Optional[Dict[str, Any]] = None, **kwargs) -> "ImagePreset":
        """
        Update the settings stored in the preset. Works like dict.update()
        """

        if values is not None:
            for k, v in values.items():
                self[k] = v

        for k, v in kwargs.items():
            self[k] = v

        return self

    def copy(self) -> "ImagePreset":
        """
        Create a new ImagePreset instance from the current one
        """

        return ImagePreset(**self._settings)

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

    def to_settings(self, model: ImageModel) -> Dict[str, Any]:
        """
        Return the values stored in the preset, for a generate_image function

        :param model: Image model to get the settings of
        """

        settings = copy.deepcopy(self._settings)

        resolution: Union[ImageResolution, Tuple[int, int]] = settings.pop("resolution")
        if isinstance(resolution, ImageResolution):
            resolution: Tuple[int, int] = resolution.value
        settings["width"], settings["height"] = resolution

        # seed 0 = random seed for the backend, but it is not set in metadata, so we set it ourself to be safe
        # the seed of the ith image is seed + i, so we reserve space for them (makes valid images with invalid metadata)
        seed = settings.pop("seed")
        if seed == 0:
            seed = random.randint(1, 0xFFFFFFFF - settings["n_samples"] + 1)
            self.last_seed = seed
        settings["seed"] = seed
        settings["extra_noise_seed"] = seed

        uc_preset: Union[UCPreset, None] = settings.pop("uc_preset")
        if uc_preset is None:
            default_uc = ""
        else:
            default_uc = self._UC_Presets[model].get(uc_preset, None)
            if default_uc is None:
                raise ValueError(f"UC preset '{uc_preset.name}' is not valid for model '{model.value}'")

        uc: str = settings.pop("uc")
        combined_uc = f"{default_uc}, {uc}" if uc else default_uc
        settings["negative_prompt"] = combined_uc

        sampler: ImageSampler = settings.pop("sampler")
        if sampler is ImageSampler.ddim and model in (ImageModel.Anime_v3,):
            sampler = ImageSampler.ddim_v3

        settings["sampler"] = sampler.value

        settings["sm"] = settings.pop("smea", False)
        settings["sm_dyn"] = settings.pop("smea_dyn", False)

        controlnet_model: Optional[ControlNetModel] = settings.pop("controlnet_model", None)
        if controlnet_model is not None:
            settings["controlnet_model"] = self._CONTROLNET_MODELS[controlnet_model]

        settings["dynamic_thresholding"] = settings.pop("decrisper")

        # special arguments kept for metadata purposes (no effect on result)
        settings["qualityToggle"] = settings.pop("quality_toggle")
        settings["ucPreset"] = uc_preset.value

        return settings

    def get_max_n_samples(self):
        """
        Get the allowed max value of ImagePreset.n_samples using current preset values
        """

        resolution: Union[ImageResolution, Tuple[int, int]] = self._settings["resolution"]

        if isinstance(resolution, ImageResolution):
            resolution: Tuple[int, int] = resolution.value

        w, h = resolution

        if w * h <= 512 * 704:
            return 8

        if w * h <= 640 * 640:
            return 6

        if w * h <= 512 * 2560:
            return 4

        if w * h <= 1024 * 1536:
            return 2

        if w * h <= 1024 * 3072:
            return 1

        return 0

    def calculate_cost(
        self, is_opus: bool, version: int = 1, generation_type: ImageGenerationType = ImageGenerationType.NORMAL
    ):
        """
        Calculate the cost (in Anlas) of generating with the current configuration

        :param is_opus: Is the subscription tier Opus ? Account for free generations if so
        :param version: Version of the model to use (1, 2, 3)
        :param generation_type: Type of generation to do (img2img, txt2img, etc.)
        """

        steps: int = self._settings["steps"]
        n_samples: int = max(1, self._settings["n_samples"])
        smea = self._settings["smea"]
        smea_dyn = self._settings["smea_dyn"]
        sampler: ImageSampler = self._settings["sampler"]

        uncond_scale: float = self._settings.get("uncond_scale", 1.0)
        strength: float = self._settings.get("strength", 1.0) if generation_type == ImageGenerationType.IMG2IMG else 1.0
        resolution: Union[ImageResolution, Tuple[int, int]] = self._settings["resolution"]

        if isinstance(resolution, ImageResolution):
            resolution: Tuple[int, int] = resolution.value

        w, h = resolution
        r = w * h
        if r < 65536:
            r = 65536

        if version == 3:
            smea_factor = 1.0 if not smea else 1.2 if not smea_dyn else 1.4
            per_sample = math.ceil(2951823174884865e-21 * r + 5.753298233447344e-7 * r * steps) * smea_factor
        else:
            if r <= 1024 * 1024 and sampler in (
                ImageSampler.plms,
                ImageSampler.ddim,
                ImageSampler.k_euler,
                ImageSampler.k_euler_ancestral,
                ImageSampler.k_lms,
            ):
                per_sample = (
                    (15.266497014243718 * math.exp(r / 1024 / 1024 * 0.6326248927474729) - 15.225164493059737)
                    * steps
                    / 28
                )
            else:
                index = math.ceil(w / 64) * math.ceil(h / 64) - 1

                if sampler is ImageSampler.nai_smea_dyn or (smea and smea_dyn):
                    per_step, fixed = SMEA_DYN_COSTS[index]
                elif sampler is ImageSampler.nai_smea or smea:
                    per_step, fixed = SMEA_COSTS[index]
                elif sampler is ImageSampler.ddim:
                    per_step, fixed = DDIM_COSTS[index]
                else:
                    per_step, fixed = NAI_COSTS[index]

                per_sample = per_step * steps + fixed

        per_sample = max(math.ceil(per_sample * strength), 2)

        if version != 1 and uncond_scale != 1.0:
            per_sample = math.ceil(per_sample * uncond_scale)

        opus_discount = is_opus and steps <= 28 and (r <= 640 * 640 if version == 1 else r <= 1024 * 1024)
        return per_sample * (n_samples - int(opus_discount))


def _get_typing_origin(t: type) -> type:
    """
    Get the typing origin of a type

    :param t: Type to get the origin of
    """

    if sys.version_info < (3, 8):  # 3.7
        origin = getattr(t, "__origin__", None)
        assert origin is not None  # should never happen for 3.7

        return origin

    return typing.get_origin(t)


def _get_typing_args(t: type) -> Tuple[type, ...]:
    """
    Get the typing arguments of a type

    :param t: Type to get the arguments of
    """

    if sys.version_info < (3, 8):  # 3.7
        args = getattr(t, "__args__", None)
        assert args is not None  # should never happen for 3.7

        return args

    return typing.get_args(t)


def _get_recursive_type(t: type, depth: int = 1) -> Union[type, Tuple[type, ...]]:
    if t is None:
        return NoneType

    if t.__module__ == "typing":
        if _get_typing_origin(t) is Union:
            if depth == 0:
                raise ValueError("Union types are not supported past depth 1")

            return tuple(_get_recursive_type(x, depth - 1) for x in _get_typing_args(t))

        return _get_typing_origin(t)

    return t


def _create_type_mapping():
    """
    Create the type mapping for the ImagePreset class
    """

    non_mapping_keys = ["last_seed"]

    for type_key, type_value in ImagePreset.__annotations__.items():
        if not type_key.startswith("_") and type_key != type_key.upper() and type_key not in non_mapping_keys:
            if type_value is float:
                type_value = (int, float)
            else:
                type_value = _get_recursive_type(type_value)

            ImagePreset._TYPE_MAPPING[type_key] = type_value  # noqa


_create_type_mapping()
