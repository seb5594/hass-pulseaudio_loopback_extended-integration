"""Load and unload loopback modules without touching anything else.

Two rules keep a switch away from the rest of the audio setup:

1. Every action runs in its own session: a fresh connection that is held
   exclusively until the action is done. PulseAudio numbers its modules per
   server run, so a module index only means something on the connection it
   was read on.
2. A module is only unloaded after it was found on that very connection and
   verified to be module-loopback with the switch's exact sink and source.
   A remembered index is never trusted: after a PulseAudio restart the same
   number can belong to a sound card or to the socket every client talks to.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
import threading
from types import MappingProxyType
from typing import Any

from pulsectl import Pulse, PulseError, PulseIndexError, PulseOperationFailed

from .arguments import ArgumentValue, format_module_argument, parse_module_argument

MODULE_NAME = "module-loopback"


class LoopbackRefused(PulseError):
    """The loopback was not loaded because it could not work or would do harm."""


@dataclass(frozen=True)
class Loopback:
    """A loopback from one source to one sink, as configured for one switch.

    Sink and source identify the loopback, the same way Home Assistant core
    recognizes it. The extra arguments only shape how it is loaded.
    """

    sink_name: str
    source_name: str
    arguments: Mapping[str, ArgumentValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Freeze the arguments too, so a loopback can never change underway."""
        object.__setattr__(self, "arguments", MappingProxyType(dict(self.arguments)))

    @property
    def module_argument(self) -> str:
        """Return the argument string, starting with sink and source like core does."""
        return format_module_argument(
            {"sink": self.sink_name, "source": self.source_name, **self.arguments}
        )

    def matches(self, module: Any) -> bool:
        """Tell whether a loaded PulseAudio module is this loopback."""
        if module.name != MODULE_NAME:
            return False
        loaded = parse_module_argument(module.argument)
        return (
            loaded.get("sink") == self.sink_name
            and loaded.get("source") == self.source_name
        )


class PulseServer:
    """One PulseAudio server, shared by every switch that talks to it."""

    def __init__(self, pulse: Pulse) -> None:
        """Wrap a pulsectl client that is created with connect=False."""
        self._pulse = pulse
        self._lock = threading.Lock()

    @property
    def connected(self) -> bool:
        """Return whether the last session reached the server."""
        return bool(self._pulse.connected)

    @contextmanager
    def session(self) -> Iterator[PulseSession]:
        """Connect afresh and keep the connection exclusive until the block ends.

        Home Assistant may run two switches of the same server at once, and
        pulsectl replaces its connection on every connect(). The lock keeps
        one switch from pulling the connection away under the other.
        """
        with self._lock:
            self._pulse.connect()
            yield PulseSession(self._pulse)


class PulseSession:
    """Loopback operations on one live connection, see PulseServer.session()."""

    def __init__(self, pulse: Pulse) -> None:
        """Bind the session to an already connected client."""
        self._pulse = pulse

    def find(self, loopback: Loopback) -> int | None:
        """Return the module index of the loopback, or None if it is not loaded."""
        indices = self._loaded_indices(loopback)
        return indices[0] if indices else None

    def load(self, loopback: Loopback) -> int:
        """Load the loopback once it is clear that it can work and cannot feed back."""
        sink = self._device(self._pulse.get_sink_by_name, "sink", loopback.sink_name)
        source = self._device(
            self._pulse.get_source_by_name, "source", loopback.source_name
        )
        if source.monitor_of_sink_name == sink.name:
            raise LoopbackRefused(
                f"source {source.name} is the monitor of sink {sink.name}, "
                "a loopback would feed the sink into itself"
            )
        return self._pulse.module_load(MODULE_NAME, loopback.module_argument)

    def unload(self, loopback: Loopback) -> int:
        """Unload every module verified as this loopback and return how many there were."""
        indices = self._loaded_indices(loopback)
        for index in indices:
            try:
                self._pulse.module_unload(index)
            except PulseOperationFailed:
                # It may have gone by itself meanwhile, for example because its
                # sink disappeared. Only a module that is still there is an error.
                if index in self._loaded_indices(loopback):
                    raise
        return len(indices)

    def _loaded_indices(self, loopback: Loopback) -> list[int]:
        """Return the indices of all loaded modules that are this loopback."""
        return [
            module.index
            for module in self._pulse.module_list()
            if loopback.matches(module)
        ]

    @staticmethod
    def _device(lookup: Callable[[str], Any], kind: str, name: str) -> Any:
        """Look up a sink or source by name and explain plainly when it is missing."""
        try:
            return lookup(name)
        except PulseIndexError:
            raise LoopbackRefused(
                f"{kind} {name} does not exist on the PulseAudio server"
            ) from None
