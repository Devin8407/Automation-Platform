"""Shared runtime infrastructure."""

from dataclasses import dataclass

from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker

from ..config import Settings


@dataclass(slots=True)
class Infrastructure:
    """Shared runtime infrastructure."""

    settings: Settings

    engine: Engine
    session_factory: sessionmaker
