from ..logging import create_logger
from .wayland_nested import IWaylandNested
from .xdotool import Xdotool


class WaylandNestedXdotool(IWaylandNested, Xdotool):
    name = "wayland_nested_xdotool"
    logger = create_logger("Input.WLNestXdo")

    @classmethod
    async def is_supported(cls):
        return (
            await IWaylandNested.is_supported() and await Xdotool.is_supported()
        )
