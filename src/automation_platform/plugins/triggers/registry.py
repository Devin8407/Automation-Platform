"""Registry of workflow trigger plugins."""

from .._registry import PluginRegistry
from ._interface import Trigger


class TriggerRegistry(PluginRegistry[Trigger]):
    """Registry of workflow trigger plugins."""

    PLUGIN_INTERFACE = Trigger
