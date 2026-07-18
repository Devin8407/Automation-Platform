"""Tests for the generic plugin registry."""

from __future__ import annotations

from typing import ClassVar

import pytest

from automation_platform.plugins._registry import PluginRegistry
from tests.fixtures.example_plugin_package.implementations.alpha import AlphaPlugin
from tests.fixtures.example_plugin_package.interface import FakePlugin

# ==============================================================================================
# Test Registry
# ==============================================================================================


class ExampleRegistry(PluginRegistry[FakePlugin]):
    """Registry backed by the example fixture plugins."""

    PLUGIN_INTERFACE = FakePlugin


# ==============================================================================================
# Test Plugins
# ==============================================================================================


class EmptyPlugin(FakePlugin):
    """Plugin with an empty plugin_type."""

    plugin_type: ClassVar[str] = ""


class DuplicatePlugin(FakePlugin):
    """Plugin with a duplicate plugin_type."""

    plugin_type: ClassVar[str] = "alpha"


# ==============================================================================================
# Construction
# ==============================================================================================


def test_registers_all_plugins() -> None:
    registry = ExampleRegistry()

    assert registry.supported_types() == {"alpha", "beta"}


# ==============================================================================================
# Public API
# ==============================================================================================


def test_get_returns_registered_plugin() -> None:
    registry = ExampleRegistry()

    assert registry.get("alpha") is AlphaPlugin


def test_get_unknown_plugin_raises_key_error() -> None:
    registry = ExampleRegistry()

    with pytest.raises(KeyError, match="Unknown plugin type"):
        registry.get("missing")


def test_contains_returns_true_for_registered_plugin() -> None:
    registry = ExampleRegistry()

    assert registry.contains("alpha")


def test_contains_returns_false_for_unknown_plugin() -> None:
    registry = ExampleRegistry()

    assert not registry.contains("missing")


def test_supported_types_returns_registered_plugin_types() -> None:
    registry = ExampleRegistry()

    assert registry.supported_types() == {"alpha", "beta"}


# ==============================================================================================
# Validation
# ==============================================================================================


def test_register_rejects_duplicate_plugin_type() -> None:
    registry = ExampleRegistry()

    with pytest.raises(ValueError, match="Duplicate plugin type"):
        registry._register(DuplicatePlugin)


def test_register_rejects_empty_plugin_type() -> None:
    registry = ExampleRegistry()

    with pytest.raises(ValueError, match="empty plugin_type"):
        registry._register(EmptyPlugin)
