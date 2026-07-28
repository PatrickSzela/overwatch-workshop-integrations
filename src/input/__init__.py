import json
from typing import cast

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


def print_keys_diff():
    keys_per_input_method = [
        set(method.key_map.keys()) for method in INPUT_METHODS
    ]

    all_keys = cast(set[str], set.union(*keys_per_input_method))
    same_keys = cast(set[str], set.intersection(*keys_per_input_method))

    for idx, method in enumerate(INPUT_METHODS):
        keys = keys_per_input_method[idx]
        print(f"{method.name}:")
        print("  Extra keys:", json.dumps(list(keys - same_keys)))
        print("  Missing keys:", json.dumps(list(all_keys - keys)))
        print()


async def get_input_method():
    method_class: type[IInput] | None = None

    for method in INPUT_METHODS:
        supported = await method.is_supported()

        if supported is True:
            method_class = method
            break

        method.logger.debug(
            "Not supported - %s",
            supported if supported else "no reason provided",
        )

    if not method_class:
        raise RuntimeError(
            "None of the implemented input methods are supported on this system!"
        )

    logger.info('Using "%s" for sending inputs', method_class.name)

    cl = method_class()
    return cl
