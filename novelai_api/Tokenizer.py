from typing import List

class Tokenizer:
    """
    Simple lazy initialization of the tokenizer as it is heavy
    """

    _tokenizer = None

    @classmethod
    def _initialize(cls):
        from transformers import GPT2Tokenizer
        cls._tokenizer = GPT2Tokenizer.from_pretrained("gpt2")

    @classmethod
    def decode(cls, o: List[int]) -> str:
        if cls._tokenizer is None:
            cls._initialize()

        return cls._tokenizer.decode(o)

    @classmethod
    def encode(cls, o: str) -> List[int]:
        if cls._tokenizer is None:
            cls._initialize()

        return cls._tokenizer.encode(o)