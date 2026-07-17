from dataclasses import dataclass
from enum import Enum
from types import UnionType


@dataclass
class Vector:
    "Representation of a vector. Each field is automatically rounded to 3 decimal places."

    x: float
    y: float
    z: float

    def __setattr__(self, name: str, value: float):
        super().__setattr__(name, round(value, 3))


class MessageDataType(Enum):
    ARRAY = 1
    BOOLEAN = 2
    NUMBER = 3
    STRING = 4
    VECTOR = 5


TYPE_MAP: dict[MessageDataType, type | UnionType] = {
    MessageDataType.ARRAY: list,
    MessageDataType.BOOLEAN: bool,
    MessageDataType.NUMBER: int | float,
    MessageDataType.STRING: str,
    MessageDataType.VECTOR: Vector,
}
