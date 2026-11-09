"""Fixtures for the PulseAudio Loopback tests."""

from collections.abc import Generator
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


def loopback_module(index: int, argument: str | None) -> SimpleNamespace:
    """Return a module-loopback entry as reported by pulsectl."""
    return SimpleNamespace(index=index, name="module-loopback", argument=argument)


@pytest.fixture
def mock_pulse() -> Generator[MagicMock]:
    """Replace the PulseAudio client with a mock without loaded modules."""
    with patch(
        "homeassistant.components.pulseaudio_loopback.switch.Pulse"
    ) as pulse_class:
        server = pulse_class.return_value
        server.connected = True
        server.module_list.return_value = []
        yield server
