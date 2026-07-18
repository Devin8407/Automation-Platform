from automation_platform.plugins._discovery import discover_plugins
from tests.fixtures.example_plugin_package.interface import FakePlugin


def test_discovers_all_plugin_implementations() -> None:
    implementations = list(discover_plugins(FakePlugin))

    names = {implementation.__name__ for implementation in implementations}

    assert names == {"AlphaPlugin", "BetaPlugin"}


def test_returns_only_plugin_subclasses() -> None:
    implementations = list(discover_plugins(FakePlugin))

    assert all(issubclass(plugin, FakePlugin) for plugin in implementations)


def test_does_not_return_interface() -> None:
    implementations = list(discover_plugins(FakePlugin))

    assert FakePlugin not in implementations


def test_does_not_return_unrelated_classes() -> None:
    implementations = list(discover_plugins(FakePlugin))

    names = {implementation.__name__ for implementation in implementations}

    assert "ignore" not in names
