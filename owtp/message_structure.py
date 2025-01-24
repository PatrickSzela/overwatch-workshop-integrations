from enum import Enum


class MessageDataType(Enum):
    ARRAY = 1
    BOOLEAN = 2
    NUMBER = 3
    STRING = 4
    VECTOR = 5


class MessageStructure:
    def __init__(
        self, name: str, id: list[int], data_types: dict[str, MessageDataType] = {}
    ):
        self._name = name
        self._id = id
        self._data_types = data_types

    @property
    def name(self):
        return self._name

    @property
    def id(self):
        return self._id

    @property
    def data_types(self):
        return self._data_types
