"""Arguments of PulseAudio's module-loopback: validation, formatting and parsing.

The rules mirror PulseAudio 17, the version Home Assistant OS ships:

* src/modules/module-loopback.c decides which arguments exist and which values
  they accept,
* src/pulsecore/modargs.c decides how an argument string is split and quoted,
* src/pulse/proplist.c decides how property lists are read.

Whatever passes validation here is accepted by PulseAudio, so a typo in the
YAML configuration shows up when Home Assistant checks the configuration and
never reaches the audio server.

Only the standard library is used, which keeps this file testable without
Home Assistant, pulsectl or a running PulseAudio server.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
import math
import re
from types import MappingProxyType
from typing import Any, Union

# A validated value as it is kept until the argument string is built.
# Property lists stay a mapping so they can be quoted safely later on.
ArgumentValue = Union[bool, int, float, str, Mapping[str, str]]
Validator = Callable[[Any], ArgumentValue]

# Limits from src/pulse/sample.h and the uint32 parser in modargs.c.
PA_RATE_MAX = 48000 * 16
PA_CHANNELS_MAX = 32
UINT32_MAX = 2**32 - 1

# PulseAudio treats exactly these characters as whitespace (C isspace()).
_WHITESPACE = " \t\n\v\f\r"
_TICK = "'"
_QUOTES = _TICK + '"'
_ESCAPE = "\\"

_PLAIN_VALUE = re.compile(r"[^ \t\n\v\f\r'\"\\]+")
_PROPERTY_KEY = re.compile(r"[\x21-\x7e]+")
_CHANNEL_MAP = re.compile(r"[a-z0-9-]+(,[a-z0-9-]+)*", re.IGNORECASE)

_TRUE_WORDS = frozenset({"1", "true", "yes", "on", "enable"})
_FALSE_WORDS = frozenset({"0", "false", "no", "off", "disable"})

# Every spelling pa_parse_sample_format() understands (case-insensitive).
SAMPLE_FORMATS = frozenset(
    {
        "u8", "8", "alaw", "ulaw", "mulaw",
        "s16le", "s16be", "s16ne", "s16re", "s16", "16",
        "s24le", "s24be", "s24ne", "s24re", "s24", "24",
        "s24-32le", "s24-32be", "s24-32ne", "s24-32re", "s24-32",
        "s32le", "s32be", "s32ne", "s32re", "s32", "32",
        "float32le", "float32be", "float32ne", "float32re", "float32", "float",
    }
)  # fmt: skip


# --- Value validators --------------------------------------------------------
# Each validator returns the normalized value or raises TypeError/ValueError
# with a message that makes sense to someone reading their configuration.yaml.


def _text(value: Any) -> str:
    """Accept strings and plain numbers, the way YAML hands them over."""
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise TypeError(f"expected text, got {value!r}")
    return str(value)


def _number(value: Any) -> float:
    """Accept finite numbers, also when YAML delivers them as text."""
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise TypeError(f"expected a number, got {value!r}")
    try:
        number = float(value)
    except ValueError:
        raise ValueError(f"expected a number, got {value!r}") from None
    if not math.isfinite(number):
        raise ValueError(f"expected a finite number, got {value!r}")
    return number


def boolean(value: Any) -> bool:
    """Accept the same spellings as Home Assistant's own boolean options."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        word = value.strip().lower()
        if word in _TRUE_WORDS:
            return True
        if word in _FALSE_WORDS:
            return False
    elif isinstance(value, (int, float)):
        return value != 0
    raise ValueError(f"expected true or false, got {value!r}")


def whole_number(minimum: int, maximum: int, zero_allowed: bool = False) -> Validator:
    """Build a validator for whole numbers within an inclusive range."""
    allowed = f"{minimum} to {maximum}"
    if zero_allowed:
        allowed = f"0 or {allowed}"

    def validate(value: Any) -> int:
        number = _number(value)
        if not number.is_integer():
            raise ValueError(f"expected a whole number, got {value!r}")
        result = int(number)
        if (zero_allowed and result == 0) or minimum <= result <= maximum:
            return result
        raise ValueError(f"expected {allowed}, got {value!r}")

    return validate


def seconds(value: Any) -> float:
    """Validate a period in seconds where 0 switches the feature off."""
    number = _number(value)
    if number == 0 or number >= 0.1:
        return number
    raise ValueError(f"expected 0 or at least 0.1 seconds, got {value!r}")


def sample_format(value: Any) -> str:
    """Validate a sample format such as s16le or float32le."""
    name = _text(value).strip().lower()
    if name in SAMPLE_FORMATS:
        return name
    raise ValueError(
        f"unknown sample format {value!r}, use for example s16le, s24le, s32le or float32le"
    )


def channel_map(value: Any) -> str:
    """Validate a channel map, given as text or as a YAML list of positions."""
    if isinstance(value, (list, tuple)):
        text = ",".join(_text(position).strip() for position in value)
    else:
        text = _text(value).replace(" ", "")
    if _CHANNEL_MAP.fullmatch(text):
        return text
    raise ValueError(
        f"expected positions like front-left,front-right or a name like stereo, got {value!r}"
    )


def properties(value: Any) -> dict[str, str]:
    """Validate a property list, written as a mapping or as PulseAudio text."""
    if isinstance(value, Mapping):
        items = {
            _property_key(key): _property_text(item) for key, item in value.items()
        }
    else:
        items = parse_property_list(_text(value))
        for key in items:
            _property_key(key)
    if not items:
        raise ValueError("expected at least one property")
    return items


def _property_key(key: Any) -> str:
    """Property keys are printable ASCII without '=' or quotes."""
    text = _text(key)
    if _PROPERTY_KEY.fullmatch(text) and not any(char in text for char in "='\""):
        return text
    raise ValueError(f"invalid property name {key!r}")


def _property_text(value: Any) -> str:
    """Keep property values as text; booleans read the same as everywhere else."""
    if isinstance(value, bool):
        return _format_scalar(value)
    return _text(value)


# The arguments module-loopback accepts, except sink and source which come from
# the switch's own sink_name and source_name options. Older PulseAudio
# versions may reject some of the newer ones, for example log_interval.
LOOPBACK_ARGUMENTS: Mapping[str, Validator] = MappingProxyType(
    {
        "adjust_time": seconds,
        "latency_msec": whole_number(1, 30000),
        "max_latency_msec": whole_number(0, UINT32_MAX),
        "log_interval": seconds,
        "fast_adjust_threshold_msec": whole_number(100, UINT32_MAX, zero_allowed=True),
        "adjust_threshold_usec": whole_number(1, 10000),
        "format": sample_format,
        "rate": whole_number(4000, PA_RATE_MAX),
        "channels": whole_number(1, PA_CHANNELS_MAX),
        "channel_map": channel_map,
        "sink_input_properties": properties,
        "source_output_properties": properties,
        "source_dont_move": boolean,
        "sink_dont_move": boolean,
        "remix": boolean,
    }
)

# Arguments the switch sets itself, mapped to the option that controls them.
RESERVED_ARGUMENTS: Mapping[str, str] = MappingProxyType(
    {"sink": "sink_name", "source": "source_name"}
)


def validate_argument(name: str, value: Any) -> ArgumentValue:
    """Validate a single module-loopback argument."""
    if name in RESERVED_ARGUMENTS:
        raise ValueError(f"'{name}' is set with the {RESERVED_ARGUMENTS[name]} option")
    validator = LOOPBACK_ARGUMENTS.get(name)
    if validator is None:
        known = ", ".join(sorted(LOOPBACK_ARGUMENTS))
        raise ValueError(
            f"'{name}' is not a module-loopback argument, known ones are: {known}"
        )
    return validator(value)


def validate_arguments(values: Any) -> dict[str, ArgumentValue]:
    """Validate a mapping of module-loopback arguments, naming the culprit on errors."""
    if not isinstance(values, Mapping):
        raise TypeError("expected a mapping of module-loopback arguments")

    validated: dict[str, ArgumentValue] = {}
    for name, value in values.items():
        try:
            validated[str(name)] = validate_argument(str(name), value)
        except (TypeError, ValueError) as err:
            raise type(err)(f"{name}: {err}") from None
    return validated


# --- Building an argument string ---------------------------------------------


def format_module_argument(arguments: Mapping[str, ArgumentValue]) -> str:
    """Build the argument string for pa_context_load_module().

    >>> format_module_argument({"sink": "speakers", "remix": False})
    'sink=speakers remix=false'
    """
    return " ".join(
        f"{name}={_format_value(value)}" for name, value in arguments.items()
    )


def _format_value(value: ArgumentValue) -> str:
    """Format one value and quote it where the modargs parser needs that."""
    if isinstance(value, Mapping):
        # module-loopback reads property lists from the raw value, without
        # unescaping it first. Every ' inside is already escaped and the text
        # ends with a double quote, so it fits between single quotes as is.
        return _TICK + _format_property_list(value) + _TICK
    return _quote(_format_scalar(value))


def _format_scalar(value: bool | int | float | str) -> str:
    """Write numbers and booleans the way PulseAudio parses them."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else repr(value)
    return str(value)


def _quote(text: str) -> str:
    """Quote text that the modargs parser would otherwise split or misread."""
    if _PLAIN_VALUE.fullmatch(text):
        return text
    return f'"{_escape(text)}"'


def _escape(text: str, *specials: str) -> str:
    """Put a backslash in front of backslashes, double quotes and any extras."""
    for char in (_ESCAPE, '"', *specials):
        text = text.replace(char, _ESCAPE + char)
    return text


def _format_property_list(values: Mapping[str, str]) -> str:
    """Write a property list with every value in escaped double quotes."""
    return " ".join(f'{key}="{_escape(value, _TICK)}"' for key, value in values.items())


# --- Reading argument strings ------------------------------------------------


def parse_module_argument(text: str | None) -> dict[str, str]:
    """Split a module argument string the way PulseAudio's modargs parser does.

    Values come back unescaped. A malformed string returns whatever could be
    read up to the problem; a module that is actually loaded never has one,
    because PulseAudio refuses to load it in the first place.

    >>> parse_module_argument('sink=speakers source="usb mic"')
    {'sink': 'speakers', 'source': 'usb mic'}
    """
    arguments: dict[str, str] = {}
    position = 0
    text = text or ""

    while (position := _skip_whitespace(text, position)) < len(text):
        key_end = _find_key_end(text, position)
        if key_end == position or not text.startswith("=", key_end):
            return arguments
        key = text[position:key_end]

        result = _read_value(text, key_end + 1, unescape_plain=True)
        if result is None:
            return arguments
        value, position = result
        # PulseAudio refuses duplicate keys, so the first one is all there is.
        arguments.setdefault(key, value)

    return arguments


def parse_property_list(text: str) -> dict[str, str]:
    """Read a property list the way pa_proplist_from_string() does.

    >>> parse_property_list("media.role=music device.description='TV room'")
    {'media.role': 'music', 'device.description': 'TV room'}
    """
    items: dict[str, str] = {}
    position = 0

    while (position := _skip_whitespace(text, position)) < len(text):
        key_end = _find_key_end(text, position)
        value_start = _skip_whitespace(text, key_end)
        if key_end == position or not text.startswith("=", value_start):
            raise ValueError(f"expected key=value pairs, got {text!r}")

        value_start = _skip_whitespace(text, value_start + 1)
        if value_start >= len(text):
            raise ValueError(f"missing value for {text[position:key_end]!r}")
        if text.startswith("hex:", value_start):
            raise ValueError("binary hex: property values are not supported")

        result = _read_value(text, value_start, unescape_plain=False)
        if result is None:
            raise ValueError(f"unterminated quote in {text!r}")
        items[text[position:key_end]], position = result

    return items


def _skip_whitespace(text: str, position: int) -> int:
    while position < len(text) and text[position] in _WHITESPACE:
        position += 1
    return position


def _find_key_end(text: str, position: int) -> int:
    while (
        position < len(text)
        and text[position] != "="
        and text[position] not in _WHITESPACE
    ):
        position += 1
    return position


def _read_value(
    text: str, position: int, unescape_plain: bool
) -> tuple[str, int] | None:
    """Read one value; returns (value, position after it) or None if it is broken.

    Quoted values end at the matching quote and a backslash escapes any
    character inside them. Plain values end at whitespace; modargs lets a
    backslash escape there too, property lists do not.
    """
    quoted = text.startswith(tuple(_QUOTES), position)
    if quoted:
        stop_chars = text[position]
        position += 1
    else:
        stop_chars = _WHITESPACE
    escaping = quoted or unescape_plain

    value: list[str] = []
    escaped = False
    while position < len(text):
        char = text[position]
        position += 1
        if escaped:
            value.append(char)
            escaped = False
        elif escaping and char == _ESCAPE:
            escaped = True
        elif char in stop_chars:
            return "".join(value), position
        else:
            value.append(char)

    # Running out of text is fine, unless a quote or an escape is still open.
    if quoted or escaped:
        return None
    return "".join(value), position
