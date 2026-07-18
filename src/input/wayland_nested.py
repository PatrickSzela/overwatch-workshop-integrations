import os
import platform
from pathlib import Path

from .input import IInput

WAYLAND_SOCKET = "wayland-nested"
XWAYLAND_DISPLAY = "1"
WAYLAND_SOCKET_PATH = Path(
    os.environ.get("XDG_RUNTIME_DIR", "/run/user/1000"), WAYLAND_SOCKET
)
XWAYLAND_SOCKET_PATH = Path("/tmp/.X11-unix/", f"X{XWAYLAND_DISPLAY}")


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
        os.environ["DISPLAY"] = f":{XWAYLAND_DISPLAY}"

        return True
