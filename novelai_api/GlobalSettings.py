from copy import deepcopy

from novelai_api.BiasGroup import BiasGroup

from typing import Dict, Any, Optional

class GlobalSettings:
    _BRACKETS = [[58],[60],[90],[92],[685],[1391],[1782],[2361],[3693],[4083],[4357],
                 [4895],[5512],[5974],[7131],[8183],[8351],[8762],[8964],[8973],[9063],
                 [11208],[11709],[11907],[11919],[12878],[12962],[13018],[13412],[14631],
                 [14692],[14980],[15090],[15437],[16151],[16410],[16589],[17241],[17414],
                 [17635],[17816],[17912],[18083],[18161],[18477],[19629],[19779],[19953],
                 [20520],[20598],[20662],[20740],[21476],[21737],[22133],[22241],[22345],
                 [22935],[23330],[23785],[23834],[23884],[25295],[25597],[25719],[25787],
                 [25915],[26076],[26358],[26398],[26894],[26933],[27007],[27422],[28013],
                 [29164],[29225],[29342],[29565],[29795],[30072],[30109],[30138],[30866],
                 [31161],[31478],[32092],[32239],[32509],[33116],[33250],[33761],[34171],
                 [34758],[34949],[35944],[36338],[36463],[36563],[36786],[36796],[36937],
                 [37250],[37913],[37981],[38165],[38362],[38381],[38430],[38892],[39850],
                 [39893],[41832],[41888],[42535],[42669],[42785],[42924],[43839],[44438],
                 [44587],[44926],[45144],[45297],[46110],[46570],[46581],[46956],[47175],
                 [47182],[47527],[47715],[48600],[48683],[48688],[48874],[48999],[49074],
                 [49082],[49146],[49946],[10221],[4841],[1427],[2602,834],[29343],[37405],
                 [35780],[2602],[50256]]
    _DINKUS_ASTERISM = BiasGroup(-0.12).add([8162], [46256, 224])

    NO_LOGPROBS = -1

    generate_until_sentence: bool
    num_logprobs: int
    ban_brackets: bool

    def __init__(self, generate_until_sentence: bool = False, num_logprobs: int = 10,
                       ban_brackets: bool = True, bias_dinkus_asterism: bool = False):
        self.generate_until_sentence = generate_until_sentence
        self.num_logprobs = num_logprobs
        self.ban_brackets = ban_brackets
        self.bias_dinkus_asterism = bias_dinkus_asterism

    def to_settings(self) -> Dict[str, Any]:
        settings = {
            "generate_until_sentence": self.generate_until_sentence,
            "num_logprobs": self.num_logprobs,

            "bad_words_ids": [],
            "logit_bias_exp": [],
            "return_full_text": False,
            "use_string": False,
            "use_cache": False,
        }

        if self.ban_brackets:
            settings["bad_words_ids"].extend(self._BRACKETS)

        if self.bias_dinkus_asterism:
            settings["logit_bias_exp"].extend(self._DINKUS_ASTERISM)

        return settings