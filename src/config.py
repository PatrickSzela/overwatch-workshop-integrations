import json
import os
from typing import TypedDict

from .utils import PROJECT_ROOT
from .logging import create_logger
from .plugin import IPlugin

logger = create_logger("ConfigManager")


class MainConfig(TypedDict):
    overwatch_dir: str


class ConfigData(TypedDict):
    main: MainConfig


DEFAULT_MAIN_CONFIG = MainConfig(
    overwatch_dir=os.path.expanduser(
        os.sep.join(["~", "My Documents", "Overwatch"])
    )
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
        exit(0)

    def load(self):
        if not os.path.isfile(CONFIG_PATH):
            self.create_default_config()

        with open(CONFIG_PATH, "r") as file:
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
                exit(0)

    def save(self):
        with open(CONFIG_PATH, "w") as file:
            obj = self.config.copy()
            file.write(json.dumps(obj, indent=4))
            file.close()
            # logger.info("Config saved!")
