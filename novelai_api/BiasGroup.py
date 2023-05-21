from typing import Any, Dict, Iterable, List, Union

from novelai_api.Preset import Model
from novelai_api.utils import tokenize_if_not


class BiasGroup:
    _sequences: List[Union[List[int], str]]

    bias: float
    ensure_sequence_finish: bool
    generate_once: bool
    enabled: bool

    def __init__(
        self,
        bias: float,
        ensure_sequence_finish: bool = False,
        generate_once: bool = False,
        enabled: bool = True,
    ):
        """
        Create a bias group

        :param bias: Bias value of the bias group. Negative is a downbias, positive is an upbias
        :param ensure_sequence_finish: Ensures the bias completes
        :param generate_once: Only biases for the first occurrence
        :param enabled: Is the bias group enabled
        """

        self._sequences = []

        self.bias = bias
        self.ensure_sequence_finish = ensure_sequence_finish
        self.generate_once = generate_once
        self.enabled = enabled

    @classmethod
    def from_data(cls, data: Dict[str, Any]) -> "BiasGroup":
        """
        Create a bias group from bias group data
        """

        # FIXME: wtf is "whenInactive" in bias ?
        ensure_sequence_finish = (
            data["ensureSequenceFinish"]
            if "ensureSequenceFinish" in data
            else data["ensure_sequence_finish"]
            if "ensure_sequence_finish" in data
            else False
        )

        generate_once = (
            data["generateOnce"]
            if "generateOnce" in data
            else data["generate_once"]
            if "generate_once" in data
            else False
        )

        b = cls(data["bias"], ensure_sequence_finish, generate_once, data["enabled"])

        if "phrases" in data:
            b.add(*data["phrases"])

        return b

    def add(
        self,
        *sequences: Union[Dict[str, List[List[int]]], Dict[str, List[int]], List[int], str],
    ) -> "BiasGroup":
        """
        Add elements to the bias group. Elements can be string or tokenized strings
        Using tokenized strings is not recommended, for flexibility between tokenizers
        """

        for i, sequence in enumerate(sequences):
            if isinstance(sequence, dict):
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

    def __iadd__(
        self, sequences: Union[Dict[str, List[List[int]]], Dict[str, List[int]], List[int], str]
    ) -> "BiasGroup":
        """
        Add elements to the bias group. Elements can be string or tokenized strings
        Using tokenized strings is not recommended, for flexibility between tokenizers
        """

        self.add(sequences)

        return self

    def __iter__(self):
        """
        Return an iterator on the stored sequences
        """

        return (
            {
                "bias": self.bias,
                "ensure_sequence_finish": self.ensure_sequence_finish,
                "generate_once": self.generate_once,
                "enabled": self.enabled,
                "sequence": s,
            }
            for s in self._sequences
        )

    def get_tokenized_entries(self, model: Model) -> Iterable[Dict[str, any]]:
        """
        Return the tokenized sequences for the bias group, if it is enabled

        :param model: Model to use for tokenization
        """

        return (
            {
                "bias": self.bias,
                "ensure_sequence_finish": self.ensure_sequence_finish,
                "generate_once": self.generate_once,
                "sequence": tokenize_if_not(model, s),
            }
            for s in self._sequences
            if self.enabled
        )

    def __str__(self) -> str:
        return (
            "{ "
            f"bias: {self.bias}, "
            f"ensure_sequence_finish: {self.ensure_sequence_finish}, "
            f"generate_once: {self.generate_once}, "
            f"enabled: {self.enabled}, "
            f"sequences: {self._sequences}"
            "}"
        )
