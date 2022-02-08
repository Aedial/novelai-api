from novelai_api.Preset import Model
from novelai_api.utils import tokenize_if_not

from typing import List, Union, Iterable, Union

class BanList:
    _sequences: List[Union[List[int], str]]

    enabled: bool

    def __init__(self, *sequences: Union[List[int], str], enabled: bool = True):
        self.enabled = enabled

        self._sequences = []
        if sequences:
            self.add(*sequences)

    def add(self, *sequences: Union[List[int], str]) -> "BanList":
        for sequence in sequences:
            if "sequence" in sequence:
                sequence = sequence["sequence"]
            elif "sequences" in sequence:
                sequence = sequence["sequences"][0]

            if type(sequence) is not str:
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

    def get_tokenized_banlist(self, model: Model) -> Iterable[List[int]]:
        return (tokenize_if_not(model, s) for s in self._sequences)

    def __str__(self) -> str:
        return self._sequences.__str__()