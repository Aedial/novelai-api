import copy
import enum
import json
import math
import os
import random
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple, Union

from novelai_api.python_utils import NoneType, expand_kwargs


class ImageModel(enum.Enum):
    """
    Image model for low_level.suggest_tags() and low_level.generate_image()
    """

    Anime_Curated = "safe-diffusion"
    Anime_Full = "nai-diffusion"
    Furry = "nai-diffusion-furry"

    Anime_Inpainting = "anime-diffusion-inpainting"


class ControlNetModel(enum.Enum):
    """
    ControlNet Model for ImagePreset.controlnet_model and low_level.generate_controlnet_mask()
    """

    Palette_Swap = "hed"
    Form_Lock = "midas"
    Scrible = "fake_scribble"
    Building_Control = "mlsd"
    Lanscaper = "uniformer"


class ImageResolution(enum.Enum):
    """
    Image resolution for ImagePreset.resolution
    """

    Small_Portrait = (384, 640)
    Small_Landscape = (640, 384)
    Small_Square = (512, 512)

    Normal_Portrait = (512, 768)
    Normal_Landscape = (768, 512)
    Normal_Square = (640, 640)

    Large_Portrait = (512, 1024)
    Large_Landscape = (1024, 512)
    Large_Square = (1024, 1024)


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


class ImageGenerationType(enum.Enum):
    """
    Image generation type for low_level.generate_image
    """

    NORMAL = "generate"
    IMG2IMG = "img2img"
    # inpainting should go there


class ImagePreset:
    _UC_Presets = {
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
    }

    _CONTROLNET_MODELS = {
        ControlNetModel.Palette_Swap: "hed",
        ControlNetModel.Form_Lock: "depth",
        ControlNetModel.Scrible: "scribble",
        ControlNetModel.Building_Control: "mlsd",
        ControlNetModel.Lanscaper: "seg",
    }

    _TYPE_MAPPING = {
        "quality_toggle": bool,
        "resolution": (ImageResolution, tuple),
        "uc_preset": (UCPreset, NoneType),
        "n_samples": int,
        "seed": int,
        "sampler": ImageSampler,
        "noise": (int, float),
        "strength": (int, float),
        "scale": (int, float),
        "steps": int,
        "uc": str,
        "smea": bool,
        "smea_dyn": bool,
        "image": str,
        "controlnet_condition": str,
        "controlnet_model": ControlNetModel,
        "controlnet_strength": (int, float),
        "decrisper": bool,
        # TODO
        # "dynamic_thresholding_mimic_scale": (int, float),
        # "dynamic_thresholding_percentile": (int, float),
    }

    # type completion for __setitem__ and __getitem__
    if TYPE_CHECKING:
        #: https://docs.novelai.net/image/qualitytags.html
        quality_toggle: bool
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

        # TODO
        # dynamic_thresholding_mimic_scale: float
        # dynamic_thresholding_percentile: float

    _DEFAULT = {
        "legacy": False,
        "quality_toggle": True,
        "resolution": ImageResolution.Normal_Portrait,
        "uc_preset": UCPreset.Preset_Low_Quality_Bad_Anatomy,
        "n_samples": 1,
        "seed": 0,
        # TODO: set ImageSampler.k_dpmpp_2m as default ?
        "sampler": ImageSampler.k_euler_ancestral,
        "steps": 28,
        "scale": 11,
        "uc": "",
        "smea": False,
        "smea_dyn": False,
        "decrisper": False,
        "controlnet_strength": 1.0,
    }

    _settings: Dict[str, Any]

    #: Seed provided when generating an image with seed 0 (default). Seed is also in metadata, but might be a hassle
    last_seed: int

    @expand_kwargs(_TYPE_MAPPING.keys(), _TYPE_MAPPING.values())
    def __init__(self, **kwargs):
        object.__setattr__(self, "_settings", self._DEFAULT.copy())
        self.update(kwargs)

        object.__setattr__(self, "last_seed", 0)

    def __setitem__(self, key: str, value: Any):
        if key not in self._TYPE_MAPPING:
            raise ValueError(f"'{key}' is not a valid setting")

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
            default_uc = self._UC_Presets[model][uc_preset]
            if default_uc is None:
                raise ValueError(f"Preset '{uc_preset.name}' is not valid for model '{model.value}'")

        uc: str = settings.pop("uc")
        combined_uc = f"{default_uc}, {uc}" if uc else default_uc
        settings["negative_prompt"] = combined_uc

        sampler: ImageSampler = settings.pop("sampler")
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

        return 1

    def calculate_cost(self, is_opus: bool):
        """
        Calculate the cost (in Anlas) of generating with the current configuration

        :param is_opus: Is the subscription tier Opus ? Account for free generations if so
        """
        steps: int = self._settings["steps"]
        n_samples: int = self._settings["n_samples"]
        resolution: Union[ImageResolution, Tuple[int, int]] = self._settings["resolution"]

        if isinstance(resolution, ImageResolution):
            resolution: Tuple[int, int] = resolution.value

        w, h = resolution

        opus_discount = is_opus & steps <= 28 and w * h <= 640 * 640

        r = w * h / 1024 / 1024
        per_step = (15.266497014243718 * math.exp(r * 0.6326248927474729) - 15.225164493059737) / 28
        per_sample = max(math.ceil(per_step * steps), 2)

        return per_sample * (n_samples - int(opus_discount))

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
