"""Registry of workflow task plugins."""

from .._registry import PluginRegistry
from ._interface import Task


class TaskRegistry(PluginRegistry[Task]):
    """Registry of workflow task plugins."""

    PLUGIN_INTERFACE = Task
