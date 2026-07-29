"Loader of :class:`IPlugin` plugins."

import importlib
import inspect
from pathlib import Path

from ..utils import PROJECT_ROOT
from ..logging import create_logger
from .plugin import IPlugin

logger = create_logger("PluginLoader")

PLUGINS_PATH = "plugins"


def load_plugins():
    "Loads all plugins that are a subclass of :class:`IPlugin` from `directory`."
    plugins: set[type[IPlugin]] = set()
    path = Path(PROJECT_ROOT, PLUGINS_PATH)

    for item in path.iterdir():
        if not item.is_dir() or not Path(item, "__init__.py").exists():
            continue

        name = item.name

        try:
            module = importlib.import_module(f"{PLUGINS_PATH}.{name}")

            for _, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, IPlugin) and not inspect.isabstract(obj):
                    plugins.add(obj)
        except BaseException as e:
            logger.warning("Failed to load plugin %s: %s", name, repr(e))

    return list(plugins)
