import json
import os
import sys
from typing import Any, TypedDict

from .logging import create_logger
from .plugin import IPlugin
from .utils import PROJECT_ROOT, validate_dict

CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.json")

logger = create_logger("ConfigManager")


class KeybindsConfig(TypedDict):
    spectate_lock_on: str
    modify_fov: str
    disable_camera_blending: str
    move_fast: str
    move_slow: str
    move_down: str
    move_up: str


class ConfigData(TypedDict):
    overwatch_dir: str
    keybinds: KeybindsConfig
    buttons_down_ticks: int
    buttons_up_ticks: int
    plugins: dict[str, Any]


DEFAULT_KEYBINDS = KeybindsConfig(
    spectate_lock_on="mouse_left",
    modify_fov="f",
    disable_camera_blending="z",
    move_fast="left_shift",
    move_slow="left_ctrl",
    move_down="q",
    move_up="e",
)

DEFAULT_CONFIG = ConfigData(
    overwatch_dir=os.path.expanduser(
        os.sep.join(["~", "My Documents", "Overwatch"])
    ),
    keybinds=DEFAULT_KEYBINDS,
    buttons_down_ticks=3,
    buttons_up_ticks=3,
    plugins={},
)


class Config:
    def __init__(self, plugins: list[type[IPlugin]]):
        self.plugins = plugins
        self.config: ConfigData

    def default_config(self):
        data = ConfigData(DEFAULT_CONFIG)

        for plugin in self.plugins:
            if plugin.config_structure():
                data["plugins"][plugin.name.lower()] = plugin.default_config()

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
                validate_dict(data, ConfigData)

                config = ConfigData(data)

                for plugin in self.plugins:
                    cls = plugin.config_structure()
                    name = plugin.name.lower()

                    if not cls:
                        continue

                    if name not in config["plugins"]:
                        raise KeyError(
                            f"No config for plugin '{plugin.name}' found in 'config.json'"
                        )

                    validate_dict(data["plugins"][name], cls, f"plugins.{name}")
                    config[name] = cls(**data["plugins"][name])

                logger.info("Config loaded")
                self.config = config
            except BaseException as e:
                logger.warning(
                    "Failed to load config file - reason: %s! Please move the existing config file to a safe place and run the application again to generate a new empty config file, and then fill it out",
                    repr(e),
                )
                sys.exit(1)

    def save(self):
        with open(CONFIG_PATH, "w", encoding="utf-8") as file:
            obj = self.config.copy()
            file.write(json.dumps(obj, indent=4))
            file.close()
            # logger.info("Config saved!")
