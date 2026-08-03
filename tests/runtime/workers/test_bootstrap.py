"""Tests for Worker runtime bootstrap."""

import signal
from unittest.mock import Mock, patch

from automation_platform.runtime.worker.bootstrap import _register_signal_handlers
from automation_platform.runtime.worker.worker import Worker


def test_register_signal_handlers_stop_worker():
    worker = Mock(spec=Worker)

    with patch("automation_platform.runtime.worker.bootstrap.signal.signal") as mock_signal:
        _register_signal_handlers(worker)

    assert mock_signal.call_count == 2

    registered_handlers = {call.args[0]: call.args[1] for call in mock_signal.call_args_list}

    assert signal.SIGINT in registered_handlers
    assert signal.SIGTERM in registered_handlers

    registered_handlers[signal.SIGINT](
        signal.SIGINT,
        None,
    )

    worker.stop.assert_called_once()
