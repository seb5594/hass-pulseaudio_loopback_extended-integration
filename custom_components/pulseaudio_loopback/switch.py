"""Switch logic for loading/unloading configurable PulseAudio loopback modules."""

from __future__ import annotations

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
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

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


def _module_value(value: Any) -> Any:
    """Validate values accepted by PulseAudio module arguments."""
    if isinstance(value, (bool, int, float, str)):
        return value
    raise probatio.Invalid("PulseAudio module argument must be string, number, or boolean")


PLATFORM_SCHEMA = SWITCH_PLATFORM_SCHEMA.extend(
    {
        probatio.Required(CONF_SINK_NAME): cv.string,
        probatio.Required(CONF_SOURCE_NAME): cv.string,
        probatio.Optional(CONF_HOST): cv.string,
        probatio.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        probatio.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
        probatio.Optional(CONF_SOURCE_DONT_MOVE, default=False): cv.boolean,
        probatio.Optional(CONF_SINK_DONT_MOVE, default=False): cv.boolean,
        probatio.Optional(CONF_ADJUST_TIME): probatio.Coerce(float),
        probatio.Optional(CONF_LATENCY_MSEC): probatio.Coerce(float),
        probatio.Optional(CONF_RATE): cv.positive_int,
        probatio.Optional(CONF_CHANNELS): cv.positive_int,
        probatio.Optional(CONF_REMIX): cv.boolean,
        probatio.Optional(CONF_FORMAT): cv.string,
        probatio.Optional(CONF_MODULE_ARGS, default={}): probatio.Schema(
            {cv.string: _module_value}
        ),
    }
)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Read all configuration and initialize the loopback switch."""
    name = config.get(CONF_NAME)
    sink_name = config.get(CONF_SINK_NAME)
    source_name = config.get(CONF_SOURCE_NAME)
    host = config.get(CONF_HOST)
    port = config.get(CONF_PORT)

    hass.data.setdefault(DOMAIN, {})


    server_id = f"{host}:{port}"

    connect_to_server = server_id if host else None

    if server_id in hass.data[DOMAIN]:
        server = hass.data[DOMAIN][server_id]
    else:
        server = Pulse(
            server=connect_to_server,
            connect=False,
            threading_lock=True,
        )
        hass.data[DOMAIN][server_id] = server

    module_args = {
        CONF_SOURCE_DONT_MOVE: config.get(CONF_SOURCE_DONT_MOVE),
        CONF_SINK_DONT_MOVE: config.get(CONF_SINK_DONT_MOVE),
        CONF_ADJUST_TIME: config.get(CONF_ADJUST_TIME),
        CONF_LATENCY_MSEC: config.get(CONF_LATENCY_MSEC),
        CONF_RATE: config.get(CONF_RATE),
        CONF_CHANNELS: config.get(CONF_CHANNELS),
        CONF_REMIX: config.get(CONF_REMIX),
        CONF_FORMAT: config.get(CONF_FORMAT),
    }

    # Remove unset optional values before building the PulseAudio argument string.
    module_args = {
        key: value for key, value in module_args.items() if value is not None
    }

    # Generic module_args can add or override any PulseAudio module-loopback argument.
    module_args.update(config.get(CONF_MODULE_ARGS, {}))

    add_entities(
        [
            PALoopbackSwitch(
                name,
                server,
                sink_name,
                source_name,
                module_args,
            )
        ],
        True,
    )


class PALoopbackSwitch(SwitchEntity):
    """Representation of the presence or absence of a PA loopback module."""

    def __init__(
        self,
        name: str,
        pa_server: Pulse,
        sink_name: str,
        source_name: str,
        module_args: dict[str, Any],
    ) -> None:
        """Initialize the PulseAudio switch."""
        self._module_idx: int | None = None
        self._name = name
        self._sink_name = sink_name
        self._source_name = source_name
        self._pa_svr = pa_server
        self._module_args = module_args

    @staticmethod
    def _format_value(value: Any) -> str:
        """Convert Python values to PulseAudio argument values."""
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)

    def _build_module_arguments(self) -> str:
        """Build module-loopback arguments compatible with pactl syntax."""
        arguments = [
            f"sink={self._sink_name}",
            f"source={self._source_name}",
        ]

        arguments.extend(
            f"{key}={self._format_value(value)}"
            for key, value in self._module_args.items()
        )

        return " ".join(arguments)

    def _get_module_idx(self) -> int | None:
        """Return the module index matching this loopback configuration."""
        try:
            self._pa_svr.connect()
            for module in self._pa_svr.module_list():
                if module.name != "module-loopback":
                    continue

                if f"sink={self._sink_name}" not in module.argument:
                    continue

                if f"source={self._source_name}" not in module.argument:
                    continue

                return module.index

        except PulseError as err:
            _LOGGER.debug("Unable to query PulseAudio modules: %s", err)

        return None

    @property
    @override
    def available(self) -> bool:
        """Return true when connected to the PulseAudio server."""
        return self._pa_svr.connected

    @property
    @override
    def name(self) -> str:
        """Return the name of the switch."""
        return self._name

    @property
    @override
    def is_on(self) -> bool:
        """Return true when the loopback module is loaded."""
        return self._module_idx is not None

    @override
    def turn_on(self, **kwargs: Any) -> None:
        """Load the configured loopback module."""
        if self.is_on:
            _LOGGER.warning(IGNORED_SWITCH_WARN)
            return

        try:
            self._pa_svr.connect()
            self._module_idx = self._pa_svr.module_load(
                "module-loopback",
                args=self._build_module_arguments(),
            )
        except PulseError as err:
            _LOGGER.error("Failed to load PulseAudio loopback module: %s", err)
            self._module_idx = None
            raise

    @override
    def turn_off(self, **kwargs: Any) -> None:
        """Unload the configured loopback module."""
        if not self.is_on:
            _LOGGER.warning(IGNORED_SWITCH_WARN)
            return

        try:
            self._pa_svr.connect()
            self._pa_svr.module_unload(self._module_idx)
            self._module_idx = None
        except PulseError as err:
            _LOGGER.error("Failed to unload PulseAudio loopback module: %s", err)
            raise

    @override
    def update(self) -> None:
        """Refresh state in case another process changed the module."""
        self._module_idx = self._get_module_idx()
