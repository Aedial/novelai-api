from os.path import abspath, dirname, join, split

from novelai_api.Preset import Model

from typing import List

tokenizers_path = join(dirname(abspath(__file__)), "tokenizers")

class Tokenizer:
    """
    Simple lazy initialization of the tokenizer as it is heavy
    """

    _tokenizer_name = {
        Model.Calliope: "gpt2",
        Model.Sigurd: "gpt2",
        Model.Euterpe_v1: "gpt2",
        Model.Euterpe: "gpt2",
        # TODO: add 20B tokenizer

        Model.Snek: "gpt2",
        Model.Genji: join(tokenizers_path, "gpt2-genji"),
    }

    _tokenizer_base = {
        "gpt2": "GPT2TokenizerFast",
        "gpt2-genji": "GPT2TokenizerFast"
    }

    _tokenizer = { }
    
    @classmethod
    def get_tokenizer_name(cls, model: Model) -> str:
        assert model in cls._tokenizer_name, f"Model {model} is not supported"

        return split(cls._tokenizer_name[model])[-1]

    @classmethod
    def _get_tokenizer(cls, model: Model) -> "PreTrainedTokenizerFast":
        tokenizer_name = cls.get_tokenizer_name(model)

        if tokenizer_name not in cls._tokenizer:
            import transformers

            assert tokenizer_name in cls._tokenizer_base
            TokenizerBase = getattr(transformers, cls._tokenizer_base[tokenizer_name])
            cls._tokenizer[tokenizer_name] = TokenizerBase.from_pretrained(cls._tokenizer_name[model])

        return cls._tokenizer[tokenizer_name]

    @classmethod
    def decode(cls, model: Model, o: List[int]) -> str:
        tokenizer = cls._get_tokenizer(model)

        return tokenizer.decode(o, verbose = False)

    @classmethod
    def encode(cls, model: Model, o: str) -> List[int]:
        tokenizer = cls._get_tokenizer(model)

        return tokenizer.encode(o, verbose = False)