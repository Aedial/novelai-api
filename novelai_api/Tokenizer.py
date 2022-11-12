from pathlib import Path
from typing import List, Union

import tokenizers

from novelai_api.ImagePreset import ImageModel
from novelai_api.Preset import Model
from novelai_api.tokenizers.simple_tokenizer import SimpleTokenizer

AnyModel = Union[Model, ImageModel]

tokenizers_path = Path(__file__).parent / "tokenizers"


class Tokenizer:
    """
    Abstraction of the tokenizer behind each Model
    """

    _tokenizers_name = {
        # Model.Calliope:             "gpt2",
        Model.Sigurd: "gpt2",
        Model.Euterpe: "gpt2",
        Model.Krake: "pile",
        Model.Snek: "gpt2",
        Model.Genji: "gpt2-genji",
        Model.HypeBot: "gpt2",
        Model.Inline: "gpt2",
        ImageModel.Anime_Curated: "clip",
        ImageModel.Anime_Full: "clip",
        ImageModel.Furry: "clip",
    }

    @classmethod
    def get_tokenizer_name(cls, model: Model) -> str:
        return cls._tokenizers_name[model]

    _GPT2_PATH = tokenizers_path / "gpt2_tokenizer.json"
    _GPT2_TOKENIZER = tokenizers.Tokenizer.from_file(str(_GPT2_PATH))

    _GENJI_PATH = tokenizers_path / "gpt2-genji_tokenizer.json"
    _GENJI_TOKENIZER = tokenizers.Tokenizer.from_file(str(_GENJI_PATH))

    _PILE_PATH = tokenizers_path / "pile_tokenizer.json"
    _PILE_TOKENIZER = tokenizers.Tokenizer.from_file(str(_PILE_PATH))

    # TODO: check differences from NAI tokenizer (from my limited testing, there is None)
    _CLIP_TOKENIZER = SimpleTokenizer()

    _tokenizers = {
        "gpt2": _GPT2_TOKENIZER,
        "gpt2-genji": _GENJI_TOKENIZER,
        "pile": _PILE_TOKENIZER,
        "clip": _CLIP_TOKENIZER,
    }

    @classmethod
    def decode(cls, model: AnyModel, o: List[int]) -> str:
        tokenizer_name = cls._tokenizers_name[model]
        tokenizer = cls._tokenizers[tokenizer_name]

        return tokenizer.decode(o)

    @classmethod
    def encode(cls, model: AnyModel, o: str) -> List[int]:
        tokenizer_name = cls._tokenizers_name[model]
        tokenizer = cls._tokenizers[tokenizer_name]

        if isinstance(tokenizer, tokenizers.Tokenizer):
            return tokenizer.encode(o).ids

        if isinstance(tokenizer, SimpleTokenizer):
            return tokenizer.encode(o)

        raise ValueError(f"Tokenizer {tokenizer} ({tokenizer_name}) not recognized")
