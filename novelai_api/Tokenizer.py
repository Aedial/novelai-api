from os.path import abspath, dirname, join, split

from novelai_api.Preset import Model

from typing import List

import tokenizers

tokenizers_path = join(dirname(abspath(__file__)), "tokenizers")

class Tokenizer:
    """
    Simple lazy initialization of the tokenizer as it is heavy
    """

    _tokenizers_name = {
        Model.Calliope:     "gpt2",
        Model.Sigurd:       "gpt2",
        Model.Euterpe:      "gpt2",
        Model.Krake:        "pile",

        Model.Snek:         "gpt2",
        Model.Genji:        "gpt2-genji",
    }

    @classmethod
    def get_tokenizer_name(cls, model: Model) -> str:
        return cls._tokenizers_name[model]

    _GPT2_PATH = join(tokenizers_path, "gpt2_tokenizer.json")
    _GPT2_TOKENIZER = tokenizers.Tokenizer.from_file(_GPT2_PATH)

    _GENJI_PATH = join(tokenizers_path, "gpt2-genji_tokenizer.json")
    _GENJI_TOKENIZER = tokenizers.Tokenizer.from_file(_GENJI_PATH)

    _PILE_PATH = join(tokenizers_path, "pile_tokenizer.json")
    _PILE_TOKENIZER = tokenizers.Tokenizer.from_file(_PILE_PATH)

    _tokenizers = {
        Model.Calliope:     _GPT2_TOKENIZER,
        Model.Sigurd:       _GPT2_TOKENIZER,
        Model.Euterpe:      _GPT2_TOKENIZER,
        Model.Krake:        _PILE_TOKENIZER,

        Model.Snek:         _GPT2_TOKENIZER,
        Model.Genji:        _GENJI_TOKENIZER,
    }

    @classmethod
    def decode(cls, model: Model, o: List[int]) -> str:
        return cls._tokenizers[model].decode(o)

    @classmethod
    def encode(cls, model: Model, o: str) -> List[int]:
        return cls._tokenizers[model].encode(o).ids