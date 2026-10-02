"""The loopback switch inside a genuine Home Assistant, configured the way users do it.

They need Home Assistant and pytest-homeassistant-custom-component. The shared
engine installs both for every release the Compatibility workflow lists; to run them
locally: python .engine/.scripts/ha_matrix.py run 2026.9.4
"""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

from homeassistant.setup import async_setup_component  # noqa: E402

CONFIG = {"switch": {
    "platform": "pulseaudio_loopback",
    "name": "paloop",
    "sink_name": "speakers",
    "source_name": "microphone",
    "rate": 48000,
    "latency_msec": 20.0,
    "remix": False,
    "module_args": {"fast_start": True},
}}
ENTITY = "switch.paloop"


@pytest.fixture
def expected_lingering_timers():
    """The switch polls PulseAudio; Home Assistant keeps that timer until it stops."""
    return True


class FakePulse:
    """A PulseAudio server without audio hardware that remembers its loaded modules."""

    connected = True

    def __init__(self):
        self.modules = []
        self.loaded = []
        self.unloaded = []

    def connect(self):
        pass

    def module_list(self):
        return list(self.modules)

    def module_load(self, name, args):
        index = 40 + len(self.loaded)
        self.loaded.append((name, args))
        self.modules.append(SimpleNamespace(name=name, argument=args, index=index))
        return index

    def module_unload(self, index):
        self.unloaded.append(index)
        self.modules = [module for module in self.modules if module.index != index]


@pytest.fixture
def pulse():
    server = FakePulse()
    with patch("custom_components.pulseaudio_loopback.switch.Pulse", return_value=server):
        yield server


async def switch(hass, service):
    await hass.services.async_call("switch", service, {"entity_id": ENTITY}, blocking=True)


async def test_yaml_platform_loads_and_starts_switched_off(hass, pulse):
    assert await async_setup_component(hass, "switch", CONFIG)
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY).state == "off"


async def test_turning_on_and_off_loads_and_unloads_the_loopback_module(hass, pulse):
    assert await async_setup_component(hass, "switch", CONFIG)
    await hass.async_block_till_done()
    await switch(hass, "turn_on")
    assert pulse.loaded == [("module-loopback", (
        "sink=speakers source=microphone source_dont_move=false sink_dont_move=false "
        "latency_msec=20 rate=48000 remix=false fast_start=true"))]
    assert hass.states.get(ENTITY).state == "on"
    await switch(hass, "turn_off")
    assert pulse.unloaded == [40]
    assert hass.states.get(ENTITY).state == "off"


async def test_an_already_loaded_module_is_picked_up_as_on(hass, pulse):
    pulse.modules.append(SimpleNamespace(
        name="module-loopback", argument="sink=speakers source=microphone", index=7))
    assert await async_setup_component(hass, "switch", CONFIG)
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY).state == "on"


async def test_an_invalid_configuration_is_rejected(hass, pulse):
    await async_setup_component(hass, "switch", {"switch": {"platform": "pulseaudio_loopback", "name": "paloop"}})
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY) is None
