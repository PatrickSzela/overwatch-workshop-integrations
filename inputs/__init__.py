import sys
from logger import create_logger
from .interface import IInput
from .linux_ydotool import Ydotool
from .windows_keyboard_mouse import KeyboardMouse

logger = create_logger("Inputs")

input: IInput

if Ydotool.is_supported():
    input = Ydotool()
elif KeyboardMouse.is_supported():
    input = KeyboardMouse()
else:
    sys.exit("No input methods are supported on this system")

logger.info(f"Using {input.name} for sending inputs")
