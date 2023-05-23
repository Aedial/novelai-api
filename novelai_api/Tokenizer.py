import itertools
from pathlib import Path
from typing import List, Union

import sentencepiece
import tokenizers

from novelai_api.ImagePreset import ImageModel
from novelai_api.Preset import Model
from novelai_api.tokenizers.simple_tokenizer import SimpleTokenizer

AnyModel = Union[Model, ImageModel]

tokenizers_path = Path(__file__).parent / "tokenizers"


class SentencePiece(sentencepiece.SentencePieceProcessor):
    """
    Wrapper around sentencepiece.SentencePieceProcessor that adds the encode and decode methods
    """

    def __init__(self, model_path: str):
        super().__init__()
        self.Load(model_path)

    def encode(self, s: str) -> List[int]:
        """
        Encode the provided text using the SentencePiece tokenizer.
        This workaround is needed because sentencepiece cannot handle `<|endoftext|>`

        :param s: Text to encode

        :return: List of tokens the provided text encodes into
        """

        parts = s.split("<|endoftext|>")

        # if there is no <|endoftext|> in the string, just encode it
        if len(parts) == 1:
            return self.EncodeAsIds(s)

        tokenized_parts: List[List[int]] = self.EncodeAsIds(parts)

        # join the tokenized parts with the token for <|endoftext|> (3). The first token is <|endoftext|>, so we skip it
        return list(itertools.chain.from_iterable([3, *part] for part in tokenized_parts))[1:]

    def decode(self, t: List[int]):
        """
        Decode the provided tokens using the SentencePiece tokenizer.

        :param t: Tokens to decode

        :return: Text the provided tokens decode into
        """

        return super().DecodeIds(t)


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
        Model.Clio: "nerdstash_v1",
        ImageModel.Anime_Curated: "clip",
        ImageModel.Anime_Full: "clip",
        ImageModel.Furry: "clip",
    }

    @classmethod
    def get_tokenizer_name(cls, model: Model) -> str:
        """
        Get the tokenizer name a model uses

        :param model: Model to get the tokenizer name of
        """

        return cls._tokenizers_name[model]

    _GPT2_PATH = tokenizers_path / "gpt2_tokenizer.json"
    _GPT2_TOKENIZER = tokenizers.Tokenizer.from_file(str(_GPT2_PATH))

    _GENJI_PATH = tokenizers_path / "gpt2-genji_tokenizer.json"
    _GENJI_TOKENIZER = tokenizers.Tokenizer.from_file(str(_GENJI_PATH))

    _PILE_PATH = tokenizers_path / "pile_tokenizer.json"
    _PILE_TOKENIZER = tokenizers.Tokenizer.from_file(str(_PILE_PATH))

    # TODO: check differences from NAI tokenizer (from my limited testing, there is None)
    _CLIP_TOKENIZER = SimpleTokenizer()

    _NERDSTASH_TOKENIZER_v1_PATH = str(tokenizers_path / "nerdstash_v1.model")
    _NERDSTASH_TOKENIZER_v1 = SentencePiece(_NERDSTASH_TOKENIZER_v1_PATH)

    _NERDSTASH_TOKENIZER_v2_PATH = str(tokenizers_path / "nerdstash_v2.model")
    _NERDSTASH_TOKENIZER_v2 = SentencePiece(_NERDSTASH_TOKENIZER_v2_PATH)

    _tokenizers = {
        "gpt2": _GPT2_TOKENIZER,
        "gpt2-genji": _GENJI_TOKENIZER,
        "pile": _PILE_TOKENIZER,
        "clip": _CLIP_TOKENIZER,
        "nerdstash_v1": _NERDSTASH_TOKENIZER_v1,
        "nerdstash_v2": _NERDSTASH_TOKENIZER_v2,
    }

    @classmethod
    def decode(cls, model: AnyModel, o: List[int]) -> str:
        """
        Decode the provided tokens using the chosen tokenizer

        :param model: Model to use the tokenizer of
        :param o: List of tokens to decode

        :return: Text the provided tokens decode into
        """

        tokenizer_name = cls._tokenizers_name[model]
        tokenizer = cls._tokenizers[tokenizer_name]

        return tokenizer.decode(o)

    @classmethod
    def encode(cls, model: AnyModel, o: str) -> List[int]:
        """
        Encode the provided text using the chosen tokenizer

        :param model: Model to use the tokenizer of
        :param o: Text to encode

        :return: List of tokens the provided text encodes into
        """

        tokenizer_name = cls._tokenizers_name[model]
        tokenizer = cls._tokenizers[tokenizer_name]

        if isinstance(tokenizer, tokenizers.Tokenizer):
            return tokenizer.encode(o).ids

        if isinstance(tokenizer, (SimpleTokenizer, sentencepiece.SentencePieceProcessor)):
            return tokenizer.encode(o)

        raise ValueError(f"Tokenizer {tokenizer} ({tokenizer_name}) not recognized")
