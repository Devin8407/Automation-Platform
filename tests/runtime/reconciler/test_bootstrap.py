"""Tests for Reconciler runtime bootstrap."""

import signal
from unittest.mock import Mock, patch

from automation_platform.runtime.reconciler import Reconciler
from automation_platform.runtime.reconciler.bootstrap import (
    _register_signal_handlers,
)


def test_register_signal_handlers_stop_reconciler():
    reconciler = Mock(spec=Reconciler)

    with patch("automation_platform.runtime.reconciler.bootstrap.signal.signal") as mock_signal:
        _register_signal_handlers(reconciler)

    registered_handlers = {call.args[0]: call.args[1] for call in mock_signal.call_args_list}

    assert signal.SIGINT in registered_handlers
    assert signal.SIGTERM in registered_handlers

    registered_handlers[signal.SIGTERM](
        signal.SIGTERM,
        None,
    )

    reconciler.stop.assert_called_once_with()
