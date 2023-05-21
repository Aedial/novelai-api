from typing import Dict, Iterable, List, Union

from novelai_api.Preset import Model
from novelai_api.utils import tokenize_if_not


class BanList:
    _sequences: List[Union[List[int], str]]

    enabled: bool

    def __init__(self, *sequences: Union[List[int], str], enabled: bool = True):
        """
        Create a ban list with the given elements. Elements can be string or tokenized strings
        Using tokenized strings is not recommended, for flexibility between tokenizers

        :param enabled: Is the ban list enabled
        """

        self.enabled = enabled

        self._sequences = []
        if sequences:
            self.add(*sequences)

    def add(
        self,
        *sequences: Union[Dict[str, List[List[int]]], Dict[str, List[int]], List[int], str],
    ) -> "BanList":
        """
        Add elements to the ban list. Elements can be string or tokenized strings
        Using tokenized strings is not recommended, for flexibility between tokenizers
        """

        for i, sequence in enumerate(sequences):
            if "sequence" in sequence:
                sequence = sequence["sequence"]
            elif "sequences" in sequence:
                sequence = sequence["sequences"][0]

            if not isinstance(sequence, str):
                if not isinstance(sequence, list):
                    raise ValueError(
                        f"Expected type 'List[int]' for sequence #{i} of 'sequences', " f"but got '{type(sequence)}'"
                    )

                for j, s in enumerate(sequence):
                    if not isinstance(s, int):
                        raise ValueError(
                            f"Expected type 'int' for item #{j} of sequence #{i} of 'sequences', "
                            f"but got '{type(s)}': {sequence}"
                        )

            self._sequences.append(sequence)

        return self

    def __iadd__(self, o: Union[List[int], str]) -> "BanList":
        """
        Add elements to the ban list. Elements can be string or tokenized strings
        Using tokenized strings is not recommended, for flexibility between tokenizers
        """

        self.add(o)

        return self

    def __iter__(self):
        """
        Return an iterator on the stored sequences
        """

        return self._sequences.__iter__()

    def get_tokenized_entries(self, model: Model) -> Iterable[List[int]]:
        """
        Return the tokenized sequences for the ban list, if it is enabled

        :param model: Model to use for tokenization
        """

        return (tokenize_if_not(model, s) for s in self._sequences if self.enabled)

    def __str__(self) -> str:
        return self._sequences.__str__()
