import os
import platform

from .input import IInput

WAYLAND_SOCKET = "wayland-nested"
XWAYLAND_DISPLAY = "1"
WAYLAND_SOCKET_PATH = f"{os.environ.get('XDG_RUNTIME_DIR')}/{WAYLAND_SOCKET}"
XWAYLAND_SOCKET_PATH = f"/tmp/.X11-unix/X{XWAYLAND_DISPLAY}"


class IWaylandNested(IInput):
    @staticmethod
    async def is_supported() -> bool:
        if (
            platform.system() != "Linux"
            or not os.path.exists(WAYLAND_SOCKET_PATH)
            or not os.path.exists(XWAYLAND_SOCKET_PATH)
        ):
            return False

        os.environ["WAYLAND_DISPLAY"] = WAYLAND_SOCKET
        os.environ["DISPLAY"] = ":1"

        return True
