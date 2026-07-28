import json
import os
import sys
from typing import TypedDict

from .logging import create_logger
from .plugin import IPlugin
from .utils import PROJECT_ROOT

logger = create_logger("ConfigManager")


class KeybindsConfig(TypedDict):
    spectate_lock_on: str
    modify_fov: str
    disable_camera_blending: str
    move_fast: str
    move_slow: str
    move_down: str
    move_up: str


class MainConfig(TypedDict):
    overwatch_dir: str
    keybinds: KeybindsConfig


class ConfigData(TypedDict):
    main: MainConfig


DEFAULT_KEYBINDS = KeybindsConfig(
    spectate_lock_on="left_ctrl",
    modify_fov="left_shift",
    disable_camera_blending="q",
    move_fast="mouse_left",
    move_slow="z",
    move_down="f",
    move_up="e",
)

DEFAULT_MAIN_CONFIG = MainConfig(
    overwatch_dir=os.path.expanduser(
        os.sep.join(["~", "My Documents", "Overwatch"])
    ),
    keybinds=DEFAULT_KEYBINDS,
)
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.json")


class Config:
    def __init__(self, plugins: list[type[IPlugin]]):
        self.plugins = plugins
        self.config: ConfigData

    def default_config(self):
        data: ConfigData = {"main": DEFAULT_MAIN_CONFIG}

        for plugin in self.plugins:
            if plugin.config_structure():
                data[plugin.name.lower()] = plugin.default_config()

        return data

    def create_default_config(self):
        self.config = self.default_config()
        self.save()
        logger.info(
            "New config file has been generated. Please fill it out and run the application again."
        )
        sys.exit()

    def load(self):
        if not os.path.isfile(CONFIG_PATH):
            self.create_default_config()

        with open(CONFIG_PATH, "r", encoding="utf-8") as file:
            try:
                data = json.load(file)
                config = ConfigData(main=MainConfig(**data["main"]))

                for plugin in self.plugins:
                    cls = plugin.config_structure()
                    if cls:
                        config[plugin.name.lower()] = cls(
                            **data[plugin.name.lower()]
                        )

                logger.info("Config loaded!")
                self.config = config
            except BaseException:
                logger.warning(
                    "Failed to load config file! Please move the existing config file to a safe place and run the application again to generate a new empty config file, and then fill it out."
                )
                sys.exit(1)

    def save(self):
        with open(CONFIG_PATH, "w", encoding="utf-8") as file:
            obj = self.config.copy()
            file.write(json.dumps(obj, indent=4))
            file.close()
            # logger.info("Config saved!")
