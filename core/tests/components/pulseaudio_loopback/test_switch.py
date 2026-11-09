"""Tests for the PulseAudio Loopback switch platform."""

from unittest.mock import MagicMock

from pulsectl import PulseError
import pytest

from homeassistant.components.pulseaudio_loopback.switch import DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from .conftest import loopback_module

ENTITY_ID = "switch.tv_loopback"
SINK = "alsa_output.hdmi"
SOURCE = "alsa_input.usb"
LOOPBACK_ARGUMENT = f"sink={SINK} source={SOURCE}"


async def _setup_switch(hass: HomeAssistant) -> None:
    """Set up a loopback switch from YAML."""
    assert await async_setup_component(
        hass,
        SWITCH_DOMAIN,
        {
            SWITCH_DOMAIN: {
                "platform": DOMAIN,
                "name": "TV loopback",
                "sink_name": SINK,
                "source_name": SOURCE,
            }
        },
    )
    await hass.async_block_till_done()


async def _call_switch(hass: HomeAssistant, service: str) -> None:
    """Call a switch service on the loopback switch."""
    await hass.services.async_call(
        SWITCH_DOMAIN, service, {ATTR_ENTITY_ID: ENTITY_ID}, blocking=True
    )


async def test_off_without_loopback(hass: HomeAssistant, mock_pulse: MagicMock) -> None:
    """Test the switch is off when no matching loopback is loaded."""
    await _setup_switch(hass)

    assert hass.states.get(ENTITY_ID).state == STATE_OFF


async def test_on_with_matching_loopback(
    hass: HomeAssistant, mock_pulse: MagicMock
) -> None:
    """Test the switch is on when its loopback is loaded."""
    mock_pulse.module_list.return_value = [loopback_module(7, LOOPBACK_ARGUMENT)]

    await _setup_switch(hass)

    assert hass.states.get(ENTITY_ID).state == STATE_ON


@pytest.mark.parametrize(
    "argument",
    [
        f"sink={SINK}.2 source={SOURCE}",
        f"sink={SINK} source={SOURCE}.monitor",
        f"sink=alsa_output.usb source=alsa_input.hdmi sink_input_properties='media.name=\"{LOOPBACK_ARGUMENT}\"'",
        None,
        "sink='unbalanced",
    ],
    ids=["longer_sink", "longer_source", "quoted_value", "no_arguments", "bad_quoting"],
)
async def test_ignores_other_loopbacks(
    hass: HomeAssistant, mock_pulse: MagicMock, argument: str | None
) -> None:
    """Test loopbacks of other sinks or sources are not mistaken for this one."""
    mock_pulse.module_list.return_value = [loopback_module(3, argument)]

    await _setup_switch(hass)

    assert hass.states.get(ENTITY_ID).state == STATE_OFF


async def test_matches_quoted_arguments(
    hass: HomeAssistant, mock_pulse: MagicMock
) -> None:
    """Test a loopback loaded with quoted values and extra arguments is found."""
    mock_pulse.module_list.return_value = [
        loopback_module(4, f"source='{SOURCE}' sink=\"{SINK}\" latency_msec=5")
    ]

    await _setup_switch(hass)

    assert hass.states.get(ENTITY_ID).state == STATE_ON


async def test_turn_on(hass: HomeAssistant, mock_pulse: MagicMock) -> None:
    """Test turning the switch on loads the loopback module."""
    await _setup_switch(hass)

    await _call_switch(hass, SERVICE_TURN_ON)

    mock_pulse.module_load.assert_called_once_with(
        "module-loopback", args=LOOPBACK_ARGUMENT
    )


async def test_turn_off_unloads_own_loopback(
    hass: HomeAssistant, mock_pulse: MagicMock
) -> None:
    """Test turning the switch off unloads its loopback and leaves others alone."""
    mock_pulse.module_list.return_value = [
        loopback_module(3, f"sink={SINK}.2 source={SOURCE}"),
        loopback_module(7, LOOPBACK_ARGUMENT),
    ]
    await _setup_switch(hass)

    await _call_switch(hass, SERVICE_TURN_OFF)

    mock_pulse.module_unload.assert_called_once_with(7)


async def test_off_when_server_fails(
    hass: HomeAssistant, mock_pulse: MagicMock
) -> None:
    """Test the switch reports off when the module list cannot be read."""
    mock_pulse.module_list.side_effect = PulseError("Connection refused")

    await _setup_switch(hass)

    assert hass.states.get(ENTITY_ID).state == STATE_OFF
