"""Switch logic for loading/unloading configurable PulseAudio loopback modules.

The structure follows homeassistant/components/pulseaudio_loopback/switch.py
on purpose, so both stay easy to compare. What differs:

* the extra module-loopback arguments, validated when the configuration is
  read (see arguments.py),
* every action resolves the module on a fresh, exclusive connection and only
  ever unloads a module verified as this switch's loopback (see loopback.py).
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
import logging
from typing import Any

# typing.override needs Python 3.12; the decorator only matters to type checkers.
try:
    from typing import override
except ImportError:

    def override(method):
        """Stand in for the typing-only decorator on older Python versions."""
        return method


# Older Home Assistant versions use voluptuous for their platform schemas.
try:
    import probatio
except ImportError:
    import voluptuous as probatio
from pulsectl import Pulse, PulseError

from homeassistant.components.switch import (
    PLATFORM_SCHEMA as SWITCH_PLATFORM_SCHEMA,
    SwitchEntity,
)
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .arguments import ArgumentValue, validate_argument, validate_arguments
from .loopback import Loopback, PulseServer, PulseSession

DOMAIN = "pulseaudio_loopback"

_LOGGER = logging.getLogger(__name__)

CONF_SINK_NAME = "sink_name"
CONF_SOURCE_NAME = "source_name"
CONF_SOURCE_DONT_MOVE = "source_dont_move"
CONF_SINK_DONT_MOVE = "sink_dont_move"
CONF_ADJUST_TIME = "adjust_time"
CONF_LATENCY_MSEC = "latency_msec"
CONF_RATE = "rate"
CONF_CHANNELS = "channels"
CONF_REMIX = "remix"
CONF_FORMAT = "format"
CONF_MODULE_ARGS = "module_args"

DEFAULT_NAME = "paloopback"
DEFAULT_PORT = 4713

IGNORED_SWITCH_WARN = "Switch is already in the desired state. Ignoring."

# Options with their own YAML key; each is passed to module-loopback under the
# same name. module_args covers every other module-loopback argument.
LOOPBACK_OPTIONS = (
    CONF_SOURCE_DONT_MOVE,
    CONF_SINK_DONT_MOVE,
    CONF_ADJUST_TIME,
    CONF_LATENCY_MSEC,
    CONF_RATE,
    CONF_CHANNELS,
    CONF_REMIX,
    CONF_FORMAT,
)


def _config_check(check: Callable[[Any], Any]) -> Callable[[Any], Any]:
    """Report a failed argument check as a regular configuration error."""

    def validate(value: Any) -> Any:
        try:
            return check(value)
        except (TypeError, ValueError) as err:
            raise probatio.Invalid(str(err)) from err

    return validate


def _loopback_option(option: str) -> Callable[[Any], Any]:
    """Validate a dedicated option with the rules of the argument it feeds."""
    return _config_check(lambda value: validate_argument(option, value))


PLATFORM_SCHEMA = SWITCH_PLATFORM_SCHEMA.extend(
    {
        probatio.Required(CONF_SINK_NAME): cv.string,
        probatio.Required(CONF_SOURCE_NAME): cv.string,
        probatio.Optional(CONF_HOST): cv.string,
        probatio.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        probatio.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
        **{
            probatio.Optional(option): _loopback_option(option)
            for option in LOOPBACK_OPTIONS
        },
        probatio.Optional(CONF_MODULE_ARGS, default={}): _config_check(
            validate_arguments
        ),
    }
)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Read in all of our configuration, and initialize the loopback switch."""
    name = config.get(CONF_NAME)
    sink_name = config.get(CONF_SINK_NAME)
    source_name = config.get(CONF_SOURCE_NAME)
    host = config.get(CONF_HOST)
    port = config.get(CONF_PORT)

    hass.data.setdefault(DOMAIN, {})

    server_id = str.format("{0}:{1}", host, port)

    if host:
        connect_to_server = server_id
    else:
        connect_to_server = None

    if server_id in hass.data[DOMAIN]:
        server = hass.data[DOMAIN][server_id]
    else:
        server = PulseServer(
            Pulse(server=connect_to_server, connect=False, threading_lock=True)
        )
        hass.data[DOMAIN][server_id] = server

    loopback = Loopback(sink_name, source_name, _loopback_arguments(name, config))
    add_entities([PALoopbackSwitch(name, server, loopback)], True)


def _loopback_arguments(name: str, config: ConfigType) -> dict[str, ArgumentValue]:
    """Merge the dedicated options with module_args, which win on overlap."""
    arguments = {
        option: config[option] for option in LOOPBACK_OPTIONS if option in config
    }
    module_args = config.get(CONF_MODULE_ARGS, {})

    for option in sorted(arguments.keys() & module_args.keys()):
        _LOGGER.warning(
            "%s: %s is set twice, using the value from %s",
            name,
            option,
            CONF_MODULE_ARGS,
        )

    arguments.update(module_args)
    return arguments


class PALoopbackSwitch(SwitchEntity):
    """Representation of the presence or absence of a PA loopback module."""

    def __init__(self, name: str, pa_server: PulseServer, loopback: Loopback) -> None:
        """Initialize the Pulseaudio switch."""
        self._module_idx: int | None = None
        self._name = name
        self._pa_svr = pa_server
        self._loopback = loopback

    def _get_module_idx(self) -> int | None:
        try:
            with self._pa_svr.session() as session:
                return session.find(self._loopback)
        except PulseError as err:
            _LOGGER.debug("Unable to query PulseAudio modules: %s", err)
            return None

    @contextmanager
    def _session(self, action: str) -> Iterator[PulseSession]:
        """Open a server session and report failures as readable errors."""
        try:
            with self._pa_svr.session() as session:
                yield session
        except PulseError as err:
            raise HomeAssistantError(f"Could not {action} {self._name}: {err}") from err

    @property
    @override
    def available(self) -> bool:
        """Return true when connected to server."""
        return self._pa_svr.connected

    @property
    @override
    def name(self) -> str:
        """Return the name of the switch."""
        return self._name

    @property
    @override
    def is_on(self) -> bool:
        """Return true if device is on."""
        return self._module_idx is not None

    @override
    def turn_on(self, **kwargs: Any) -> None:
        """Turn the device on."""
        with self._session("turn on") as session:
            module_idx = session.find(self._loopback)
            if module_idx is None:
                module_idx = session.load(self._loopback)
            else:
                _LOGGER.warning(IGNORED_SWITCH_WARN)
        self._module_idx = module_idx

    @override
    def turn_off(self, **kwargs: Any) -> None:
        """Turn the device off."""
        with self._session("turn off") as session:
            if not session.unload(self._loopback):
                _LOGGER.warning(IGNORED_SWITCH_WARN)
        self._module_idx = None

    def update(self) -> None:
        """Refresh state in case an alternate process modified this data."""
        self._module_idx = self._get_module_idx()
