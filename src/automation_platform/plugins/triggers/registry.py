"""Registry of workflow trigger plugins."""

from .._registry import PluginRegistry
from .interface import Trigger


class TaskRegistry(PluginRegistry[Trigger]):
    """Registry of workflow trigger plugins."""

    PLUGIN_INTERFACE = Trigger
