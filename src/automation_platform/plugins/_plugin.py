"""Base plugin class"""

from __future__ import annotations

from abc import ABC
from typing import ClassVar


class Plugin(ABC):
    """Base plugin class"""

    plugin_type: ClassVar[str]
