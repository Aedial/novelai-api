from base64 import urlsafe_b64encode
from os import urandom
from typing import Set


class Idstore:
    _ID_SIZE = 21
    _ids: Set[str]

    def __init__(self):
        self._ids = set()

    def _create_id(self) -> str:
        b = urandom(self._ID_SIZE)
        strid = urlsafe_b64encode(b).decode()

        return strid[: self._ID_SIZE]

    def register(self, *args):
        """
        Registers the ids in every item provided (must be retrieved with download_user_content)
        """

        for e in args:
            if "id" in e:
                self._ids.add(e["id"])

    def create(self) -> str:
        """
        Create a new unique id, that hasn't been registered yet, and register it

        :return: Created id
        """
        new_id = next(iter(self._ids))
        while new_id in self._ids:
            new_id = self._create_id()

        self._ids.add(new_id)

        return new_id
