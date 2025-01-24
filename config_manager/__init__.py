import os
import json
from logger import create_logger

logger = create_logger("ConfigManager")


CONFIG_PATH = "./config.json"


class Config:
    def __init__(self):
        # TODO: move Twitch's stuff to module
        self.twitch_app_id = ""
        self.twitch_app_secret = ""
        self.twitch_last_channel = ""
        self.overwatch_dir = os.path.expanduser(
            os.sep.join(["~", "My Documents", "Overwatch"])
        )

        self._has_unsaved_changes: bool = False

    def __setattr__(self, name, value):
        if (
            isinstance(name, str)
            and not name.startswith("_")
            and hasattr(self, name)
            and getattr(self, name) != value
        ):
            self._has_unsaved_changes = True

        super().__setattr__(name, value)

    @property
    def has_unsaved_changes(self):
        return self._has_unsaved_changes

    def load(self):
        if not os.path.isfile(CONFIG_PATH):
            return

        with open(CONFIG_PATH, "r") as file:
            try:
                config = json.load(file)

                # TODO: make sure config file has a proper structure
                for key in config:
                    setattr(self, key, config[key])

                self._has_unsaved_changes = False
                logger.info(f"Config loaded!")
            except BaseException:
                logger.warning("Failed while loading config file!")

    def ask_for_missing_data(self):
        while not self.overwatch_dir or not os.path.isdir(self.overwatch_dir):
            logger.warning(
                f'Overwatch directory "{self.overwatch_dir}" doesn\'t exists...'
            )
            self.overwatch_dir = input(
                "Enter path to the Overwatch directory in your Documents folder: "
            )

        if not self.twitch_app_id:
            self.twitch_app_id = input("Enter Twitch's application ID: ")

        if not self.twitch_app_secret:
            self.twitch_app_secret = input("Enter Twitch's application secret key: ")

    def save_if_necessary(self):
        if self.has_unsaved_changes:
            self.save()

    def save(self):
        with open(CONFIG_PATH, "w") as file:
            obj = self.__dict__.copy()
            obj = {key: obj[key] for key in obj if not key.startswith("_")}
            file.write(json.dumps(obj, indent=4))
            file.close()
            self._has_unsaved_changes = False
            logger.info("Config saved!")


def initialize():
    config = Config()
    config.load()
    config.ask_for_missing_data()
    config.save_if_necessary()

    return config
