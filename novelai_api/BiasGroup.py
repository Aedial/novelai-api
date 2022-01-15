from novelai_api.Tokenizer import Tokenizer

from typing import List, Union

class BiasGroup:
    _sequences: List[List[int]]
    bias: float
    ensure_sequence_finish: bool
    generate_once: bool

    def __init__(self, bias: float, ensure_sequence_finish: bool = False, generate_once: bool = False):
        self._sequences = []

        self.bias = bias
        self.ensure_sequence_finish = ensure_sequence_finish
        self.generate_once = generate_once

    def add(self, *sequences: Union[List[int], str]) -> "BiasGroup":
        for sequence in sequences:
            if type(sequence) is str:
                sequence = Tokenizer.encode(sequence)
            else:
                assert type(sequence) is list, f"Expected type 'List[int]' for sequence, but got '{type(sequence)}'"
                for i, s in enumerate(sequence):
                    assert type(s) is int, f"Expected type 'int' for item #{i} of sequence, but got '{type(s)}: {sequence}'"

            self._sequences.append(sequence)

        return self

    def __iadd__(self, o: List[int]) -> "BiasGroup":
        self.add(o)

        return self

    def __iter__(self):
        return ({ "bias": self.bias,
                  "ensure_sequence_finish": self.ensure_sequence_finish,
                  "generate_once": self.generate_once,
                  "sequence": s } for s in self._sequences)

    def __str__(self) -> str:
        return "{ " \
                    f"bias: {self.bias}, " \
                    f"ensure_sequence_finish: {self.ensure_sequence_finish}, " \
                    f"generate_once: {self.generate_once}, " \
                    f"sequences: {self._sequences}" \
                "}"