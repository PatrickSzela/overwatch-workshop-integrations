from ..logging import create_logger
from .input import IInput
from .keyboard_mouse import KeyboardMouse
from .wayland_nested_xdotool import WaylandNestedXdotool
from .xdotool import Xdotool
from .ydotool import Ydotool

logger = create_logger("Input")

INPUT_METHODS: list[type[IInput]] = [
    WaylandNestedXdotool,
    Ydotool,
    Xdotool,
    KeyboardMouse,
]

# xdo = set(Xdotool.key_map.keys())
# ydo = set(Ydotool.key_map.keys())
# kbm = set(KeyboardMouse.key_map.keys())
# all_keys = xdo | ydo | kbm

# print("Not in xdotool: ", all_keys - xdo)
# print("Not in ydotool: ", all_keys - ydo)
# print("Not in keyboard_mouse: ", all_keys - kbm)
# exit()


async def get_input_method():
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
    return cl
