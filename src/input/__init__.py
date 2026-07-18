from ..logging import create_logger
from .input import IInput
from .keyboard_mouse import KeyboardMouse
from .wayland_nested_xdotool import WaylandNestedXdotool
from .xdotool import Xdotool
from .ydotool import Ydotool

logger = create_logger("Inputs")

INPUT_METHODS: list[type[IInput]] = [
    WaylandNestedXdotool,
    Ydotool,
    Xdotool,
    KeyboardMouse,
]


async def initialize():
    input_class: type[IInput] | None = None

    for i in INPUT_METHODS:
        if await i.is_supported():
            input_class = i
            break

    if not input_class:
        raise RuntimeError(
            "None of the implemented input methods are supported on this system!"
        )

    logger.info('Using "%s" for sending inputs', input_class.name)

    cl = input_class()
    await cl.initialize()
    return cl
