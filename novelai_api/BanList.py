from novelai_api.Tokenizer import Tokenizer

from typing import List, Union

class BanList:
    _sequences: List[List[int]]

    enabled: bool

    def __init__(self, *sequences: Union[List[int], str], enabled: bool = True):
        self._sequences = []
        if sequences:
            self.add(*sequences)

    def add(self, *sequences: Union[List[int], str]) -> "BanList":
        for sequence in sequences:
            if "sequence" in sequence:
                sequence = sequence["sequence"]
            elif "sequences" in sequence:
                sequence = sequence["sequences"][0]

            if type(sequence) is str:
                sequence = Tokenizer.encode(sequence)
            else:
                assert type(sequence) is list, f"Expected type 'List[int]' for sequence, but got '{type(sequence)}'"
                for i, s in enumerate(sequence):
                    assert type(s) is int, f"Expected type 'int' for item #{i} of sequence, but got '{type(s)}: {sequence}'"

            self._sequences.append(sequence)

        return self

    def __iadd__(self, o: Union[List[int], str]) -> "BanList":
        self.add(o)

        return self

    def __iter__(self):
        return self._sequences.__iter__()

    def __str__(self) -> str:
        return self._sequences.__str__()