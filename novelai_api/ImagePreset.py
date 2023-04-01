import copy
import enum
import json
import math
import random
from typing import Any, Dict


class ImageModel(enum.Enum):
    Anime_Curated = "safe-diffusion"
    Anime_Full = "nai-diffusion"
    Furry = "nai-diffusion-furry"


class ControlNetModel(enum.Enum):
    Palette_Lock = "hed"
    Form_Lock = "midas"
    Scrible = "fake_scribble"
    Building_Control = "mlsd"
    Lanscaper = "uniformer"


class ImageResolution(enum.Enum):
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
    k_lms = "k_lms"
    k_euler = "k_euler"
    k_euler_ancestral = "k_euler_ancestral"
    k_heun = "k_heun"  # api doesn't work
    plms = "plms"  # api2 doesn't work
    ddim = "ddim"

    nai_smea = "nai_smea"  # api, api2 doesn't work
    nai_smea_dyn = "nai_smea_dyn"  # api doesn't work

    k_dpmpp_2m = "k_dpmpp_2m"
    k_dpmpp_2s_ancestral = "k_dpmpp_2s_ancestral"
    k_dpmpp_sde = "k_dpmpp_sde"
    k_dpm_2 = "k_dpm_2"
    k_dpm_2_ancestral = "k_dpm_2_ancestral"  # api doesn't work
    k_dpm_adaptive = "k_dpm_adaptive"  # api doesn't work
    k_dpm_fast = "k_dpm_fast"


class UCPreset(enum.Enum):
    Preset_Low_Quality_Bad_Anatomy = 2
    Preset_Low_Quality = 1
    Preset_None = 0
    Preset_Custom = -1


class ImagePreset:
    _UC_Presets = {
        ImageModel.Anime_Curated: {
            UCPreset.Preset_Low_Quality_Bad_Anatomy: "nsfw, lowres, bad anatomy, bad hands, text, error, "
            "missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, "
            "jpeg artifacts, signature, watermark, twitter username, blurry",
            UCPreset.Preset_Low_Quality: "nsfw, lowres, text, cropped, worst quality, low quality, normal quality, "
            "jpeg artifacts, signature, watermark, twitter username, blurry",
            UCPreset.Preset_None: "lowres",
            UCPreset.Preset_Custom: "",
        },
        ImageModel.Anime_Full: {
            UCPreset.Preset_Low_Quality_Bad_Anatomy: "lowres, bad anatomy, bad hands, text, error, missing fingers, "
            "extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, "
            "signature, watermark, username, blurry",
            UCPreset.Preset_Low_Quality: "lowres, text, cropped, worst quality, low quality, normal quality, "
            "jpeg artifacts, signature, watermark, username, blurry",
            UCPreset.Preset_None: "lowres",
            UCPreset.Preset_Custom: "",
        },
        ImageModel.Furry: {
            UCPreset.Preset_Low_Quality: "nsfw, worst quality, low quality, what has science done, what, "
            "nightmare fuel, eldritch horror, where is your god now, why",
            UCPreset.Preset_None: "low res",
            UCPreset.Preset_Custom: "",
        },
    }

    _CONTROLNET_MODELS = {
        ControlNetModel.Palette_Lock: "hed",
        ControlNetModel.Form_Lock: "depth",
        ControlNetModel.Scrible: "scribble",
        ControlNetModel.Building_Control: "mlsd",
        ControlNetModel.Lanscaper: "seg",
    }

    _TYPE_MAPPING = {
        "quality_toggle": bool,
        # (width, height)
        "resolution": (ImageResolution, tuple),
        # default UC to prepend to the uc
        "uc_preset": UCPreset,
        # number of images to return
        "n_samples": int,
        # random seed
        "seed": int,
        # see official docs
        "sampler": ImageSampler,
        # see official docs
        "noise": (int, float),
        # 0-1 factor to which steps are multiplied in img2img
        "strength": (int, float),
        # see official docs
        "scale": (int, float),
        # see official docs
        "steps": int,
        # Undesired Content
        "uc": str,
        # use SMEA mode
        "smea": bool,
        # use DYN mode for SMEA
        "smea_dyn": bool,
        # png image b64 encoded for img2img
        "image": str,
        # controlnet mask gotten by the generate_controlnet_mask method
        "controlnet_condition": str,
        # model to use for the controlnet
        "controlnet_model": ControlNetModel,
        # ???
        "dynamic_thresholding": bool,
    }

    _DEFAULT = {
        "quality_toggle": True,
        "resolution": ImageResolution.Normal_Portrait,
        "uc_preset": UCPreset.Preset_Low_Quality_Bad_Anatomy,
        "n_samples": 1,
        "seed": 0,
        "sampler": ImageSampler.k_euler_ancestral,
        "noise": 0.2,
        "strength": 0.7,
        "steps": 28,
        "scale": 11,
        "uc": "",
        "smea": False,
        "smea_dyn": False,
    }

    _settings: Dict[str, Any]

    # Seed provided when generating an image with seed 0 (default). Seed is also in metadata, but might be a hassle
    last_seed: int

    def __init__(self, **kwargs):
        self._settings = self._DEFAULT.copy()
        self.update(kwargs)

        self.last_seed = 0

    def __setitem__(self, key: str, value: Any):
        if key not in self._TYPE_MAPPING:
            raise ValueError(f"'{key}' is not a valid setting")

        if isinstance(value, self._TYPE_MAPPING[key]):
            ValueError(f"Expected type '{self._TYPE_MAPPING[key]}' for {key}, but got type '{type(value)}'")

        self._settings[key] = value

    def __delitem__(self, key):
        if key in self._DEFAULT:
            raise ValueError(f"{key} is a default setting, set it instead of deleting")

        del self._settings[key]

    def update(self, values: Dict[str, Any]) -> "ImagePreset":
        for k, v in values.items():
            self[k] = v

        return self

    def copy(self) -> "ImagePreset":
        return ImagePreset(**self._settings)

    def __contains__(self, o: str):
        return o in self._settings

    def __getitem__(self, o: str):
        return self._settings[o]

    def to_settings(self, model: ImageModel) -> Dict[str, Any]:
        settings = copy.deepcopy(self._settings)

        resolution = settings.pop("resolution")
        if isinstance(resolution, ImageResolution):
            resolution = resolution.value
        settings["width"], settings["height"] = resolution

        if settings["seed"] == 0:
            settings["seed"] = random.randint(1, 0xFFFFFFFF)
            self.last_seed = settings["seed"]

        uc_preset: UCPreset = settings.pop("uc_preset")

        uc: str = settings.pop("uc")
        default_uc = self._UC_Presets[model][uc_preset]
        combined_uc = f"{default_uc}, {uc}" if uc else default_uc
        settings["uc"] = combined_uc

        sampler: ImageSampler = settings.pop("sampler")
        settings["sampler"] = sampler.value

        if settings.pop("smea", False):
            settings["sm"] = True

            if settings.pop("smea_dyn", False):
                settings["sm_dyn"] = True

        controlnet_model = settings.pop("controlnet_model", None)
        if controlnet_model is not None:
            settings["controlnet_model"] = self._CONTROLNET_MODELS[controlnet_model]

        # special arguments kept for metadata purposes (no effect on result)
        settings["qualityToggle"] = settings.pop("quality_toggle")
        settings["ucPreset"] = uc_preset.value

        return settings

    def get_max_n_samples(self):
        resolution = self._settings["resolution"]

        if isinstance(resolution, ImageResolution):
            resolution = resolution.value

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
        steps = self._settings["steps"]
        n_samples = self._settings["n_samples"]
        resolution = self._settings["resolution"]

        if isinstance(resolution, ImageResolution):
            resolution = resolution.value

        w, h = resolution

        if is_opus and n_samples == 1 and steps <= 28 and w * h <= 640 * 640:
            return 0

        r = w * h / 1024 / 1024
        per_step = (15.266497014243718 * math.exp(r * 0.6326248927474729) - 15.225164493059737) / 28
        per_sample = max(math.ceil(per_step * steps), 2)

        return per_sample * n_samples

    @classmethod
    def from_file(cls, path: str) -> "ImagePreset":
        with open(path, encoding="utf-8") as f:
            data = json.loads(f.read())

        return cls(**data)

    def to_file(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            f.write(json.dumps(self._settings))
