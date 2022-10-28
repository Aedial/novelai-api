import enum
import copy
import json
import math
import random

from typing import Dict, Any


class ImageModel(enum.Enum):
    Anime_Curated = "safe-diffusion"
    Anime_Full = "nai-diffusion"
    Furry = "nai-diffusion-furry"


class ImageResolution(enum.Enum):
    Small_Portrait      = ( 384,  640)
    Small_Landscape     = ( 640,  384)
    Small_Square        = ( 512,  512)

    Normal_Portrait     = ( 512,  768)
    Normal_Landscape    = ( 768,  512)
    Normal_Square       = ( 640,  640)

    Large_Portrait      = ( 512, 1024)
    Large_Landscape     = (1024,  512)
    Large_Square        = (1024, 1024)


class ImageSampler(enum.Enum):
    k_lms = "k_lms"
    k_euler = "k_euler"
    k_euler_ancestral = "k_euler_ancestral"
    plms = "plms"
    ddim = "ddim"


class UCPreset(enum.Enum):
    Preset_Low_Quality_Bad_Anatomy = 2
    Preset_Low_Quality = 1
    Preset_None = 0


class ImagePreset:
    _UC_Presets = {
        ImageModel.Anime_Curated: {
            UCPreset.Preset_Low_Quality_Bad_Anatomy:
                "nsfw, lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, "
                "cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, "
                "twitter username, blurry",
            UCPreset.Preset_Low_Quality:
                "nsfw, lowres, text, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature,"
                "watermark, twitter username, blurry",
            UCPreset.Preset_None: "lowres"
        },
        ImageModel.Anime_Full: {
            UCPreset.Preset_Low_Quality_Bad_Anatomy:
                "lowres, bad anatomy, bad hands, text, error, missing fingers, "
                "extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, "
                "signature, watermark, username, blurry",
            UCPreset.Preset_Low_Quality:
                "lowres, text, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, "
                "watermark, username, blurry",
            UCPreset.Preset_None: "lowres"
        },
        ImageModel.Furry: {
            UCPreset.Preset_Low_Quality: "nsfw, {worst quality}, {bad quality}, text, signature, watermark",
            UCPreset.Preset_None: "low res"
        }
    }

    _TYPE_MAPPING = {
        "quality_toggle": bool,
        "resolution":       (ImageResolution, tuple),
        "uc_preset":        UCPreset,

        "n_samples":        int,
        "seed":             int,
        "sampler":          ImageSampler,
        "noise":            (int, float),
        "strength":         (int, float),
        "scale":            (int, float),
        "steps":            int,
        "uc":               str
    }

    _DEFAULT = {
        "quality_toggle": True,
        "resolution":       ImageResolution.Normal_Portrait,
        "uc_preset":        UCPreset.Preset_Low_Quality_Bad_Anatomy,

        "n_samples":        1,
        "seed":             0,
        "sampler":          ImageSampler.k_euler_ancestral,
        "noise":            0.2,
        "strength":         0.7,
        "steps":            28,
        "scale":            11,
        "uc":               ""
    }

    _settings: Dict[str, Any]

    def __init__(self, **kwargs):
        self._settings = self._DEFAULT.copy()
        self.update(kwargs)

    def __setitem__(self, o: str, v: Any):
        assert o in self._TYPE_MAPPING, f"'{o}' is not a valid setting"
        assert isinstance(v, self._TYPE_MAPPING[o]), \
            f"Expected type '{self._TYPE_MAPPING[o]}' for {o}, but got type '{type(v)}'"

        self._settings[o] = v

    def update(self, values: Dict[str, Any]) -> "ImagePreset":
        for k, v in values.items():
            self.__setitem__(k, v)

        return self

    def copy(self) -> "ImagePreset":    return ImagePreset(**self._settings)
    def __contains__(self, o: str):     return self._settings.__contains__(o)
    def __getitem__(self, o: str):      return self._settings.__getitem__(o)

    def to_settings(self, model: ImageModel) -> Dict[str, Any]:
        settings = copy.deepcopy(self._settings)

        del settings["quality_toggle"]

        resolution = settings.pop("resolution")
        if type(resolution) is ImageResolution:
            resolution = resolution.value
        settings["width"], settings["height"] = resolution

        if settings["seed"] == 0:
            settings["seed"] = random.randint(1, 0xFFFFFFFF)

        uc_preset: UCPreset = settings.pop("uc_preset")
        uc: str = settings.pop("uc")
        default_uc = self._UC_Presets[model][uc_preset]
        combined_uc = f"{default_uc}, {uc}" if uc else default_uc
        settings["uc"] = combined_uc

        sampler: ImageSampler = settings.pop("sampler")
        settings["sampler"] = sampler.value

        return settings

    def get_max_n_samples(self):
        resolution = self._settings["resolution"]

        if type(resolution) is ImageResolution:
            resolution = resolution.value

        w, h = resolution

        if w * h < 512 * 1024:
            return 4
        else:
            return 1

    def calculate_cost(self, is_opus: bool):
        steps = self._settings["steps"]
        n_samples = self._settings["n_samples"]
        resolution = self._settings["resolution"]

        if type(resolution) is ImageResolution:
            resolution = resolution.value

        w, h = resolution

        if is_opus and n_samples == 1 and steps <= 28 and w * h <= 640 * 640:
            return 0

        r = w * h / 1024 / 1024
        per_step = (15.266497014243718 * math.exp(r * .6326248927474729) - 15.225164493059737) / 28
        per_sample = max(math.ceil(per_step * steps), 2)

        return per_sample * n_samples

    @classmethod
    def from_file(cls, path: str) -> "ImagePreset":
        with open(path, encoding = "utf-8") as f:
            data = json.loads(f.read())

        return cls(**data)

    def to_file(self, path: str):
        with open(path, 'w', encoding = "utf-8") as f:
            f.write(json.dumps(self._settings))
