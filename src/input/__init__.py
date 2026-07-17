from ..logging import create_logger
from .input import IInput
from .keyboard_mouse import KeyboardMouse
from .kwin_nested import KwinNested
from .ydotool import Ydotool

logger = create_logger("Inputs")

INPUT_METHODS: list[type[IInput]] = [KwinNested, Ydotool, KeyboardMouse]


def initialize():
    input_class = next((i for i in INPUT_METHODS if i.is_supported()), None)

    if not input_class:
        raise RuntimeError(
            "None of the implemented input methods are supported on this system!"
        )

    logger.info('Using "%s" for sending inputs', input_class.name)
    return input_class()
