from novelai_api.Preset import Model

from typing import List

class Tokenizer:
    """
    Simple lazy initialization of the tokenizer as it is heavy
    """

    _tokenizer_name = {
        Model.Calliope: "gpt2",
        Model.Euterpe: "gpt2",
        Model.Sigurd: "gpt2",
        Model.Snek: "gpt2",
        # FIXME: genji isn't in HF's API
#        Model.Genji: "gpt2-genji",
        # add 20B tokenizer
    }

    _tokenizer = { }
    
    @classmethod
    def _get_tokenizer(cls, model: Model) ->  "PreTrainedTokenizerFast":
        assert model in cls._tokenizer_name, f"Model {model} is not supported"

        tokenizer_name = cls._tokenizer_name[model]

        if tokenizer_name not in cls._tokenizer:
            from transformers import  PreTrainedTokenizerFast
            cls._tokenizer[tokenizer_name] =  PreTrainedTokenizerFast.from_pretrained(tokenizer_name)

        return cls._tokenizer[tokenizer_name]

    @classmethod
    def decode(cls, model: Model, o: List[int]) -> str:
        tokenizer = cls._get_tokenizer(model)

        return tokenizer.decode(o, verbose = False)

    @classmethod
    def encode(cls, model: Model, o: str) -> List[int]:
        tokenizer = cls._get_tokenizer(model)

        return tokenizer.encode(o, verbose = False)