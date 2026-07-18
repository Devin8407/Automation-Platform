from abc import ABC
from typing import ClassVar


class FakePlugin(ABC):
    plugin_type: ClassVar[str]
