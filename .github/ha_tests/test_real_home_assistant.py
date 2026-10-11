"""The loopback switch inside a genuine Home Assistant, configured the way users do it.

They need Home Assistant and pytest-homeassistant-custom-component. The shared
engine installs both for every release the Compatibility workflow lists; to run them
locally: python .engine/.scripts/ha_matrix.py run 2026.9.4
"""

import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")

try:
    import pulsectl  # noqa: F401
except OSError:
    # pulsectl loads libpulse on import; CI runners without it get a stand-in,
    # the tests replace the client anyway.
    stand_in = ModuleType("pulsectl")
    stand_in.PulseError = type("PulseError", (Exception,), {})
    for error in ("PulseIndexError", "PulseOperationFailed"):
        setattr(stand_in, error, type(error, (stand_in.PulseError,), {}))
    stand_in.Pulse = object
    sys.modules["pulsectl"] = stand_in

from pulsectl import PulseIndexError, PulseOperationFailed  # noqa: E402

from homeassistant.exceptions import HomeAssistantError  # noqa: E402
from homeassistant.setup import async_setup_component  # noqa: E402

PLATFORM = {
    "platform": "pulseaudio_loopback",
    "name": "paloop",
    "sink_name": "speakers",
    "source_name": "microphone",
}
CONFIG = {
    "switch": {
        **PLATFORM,
        "rate": 48000,
        "latency_msec": 20.0,
        "remix": False,
        "module_args": {"adjust_time": 2},
    }
}
ENTITY = "switch.paloop"


@pytest.fixture
def expected_lingering_timers():
    """The switch polls PulseAudio; Home Assistant keeps that timer until it stops."""
    return True


class FakePulse:
    """A PulseAudio server without audio hardware that remembers its loaded modules.

    Like the real one it numbers modules per run, so a restart hands out the
    same indices again.
    """

    connected = True

    def __init__(self):
        self.loaded = []
        self.unloaded = []
        self.restart()

    def restart(self):
        self.modules = []
        self.next_index = 0
        for name in ("module-udev-detect", "module-native-protocol-unix"):
            self.add(name, "")

    def add(self, name, argument):
        self.modules.append(
            SimpleNamespace(name=name, argument=argument, index=self.next_index)
        )
        self.next_index += 1
        return self.next_index - 1

    def connect(self):
        pass

    def module_list(self):
        return list(self.modules)

    def module_load(self, name, args):
        self.loaded.append((name, args))
        return self.add(name, args)

    def module_unload(self, index):
        if all(module.index != index for module in self.modules):
            raise PulseOperationFailed(index)
        self.unloaded.append(index)
        self.modules = [module for module in self.modules if module.index != index]

    def get_sink_by_name(self, name):
        if name != "speakers":
            raise PulseIndexError(name)
        return SimpleNamespace(name=name)

    def get_source_by_name(self, name):
        if name != "microphone":
            raise PulseIndexError(name)
        return SimpleNamespace(name=name, monitor_of_sink_name=None)

    def names(self):
        return [module.name for module in self.modules]


@pytest.fixture
def pulse():
    server = FakePulse()
    with patch(
        "custom_components.pulseaudio_loopback.switch.Pulse", return_value=server
    ):
        yield server


async def switch(hass, service):
    await hass.services.async_call(
        "switch", service, {"entity_id": ENTITY}, blocking=True
    )


async def setup(hass, config=CONFIG):
    assert await async_setup_component(hass, "switch", config)
    await hass.async_block_till_done()


async def test_yaml_platform_loads_and_starts_switched_off(hass, pulse):
    await setup(hass)
    assert hass.states.get(ENTITY).state == "off"


async def test_turning_on_and_off_loads_and_unloads_the_loopback_module(hass, pulse):
    await setup(hass)
    await switch(hass, "turn_on")
    assert pulse.loaded == [
        (
            "module-loopback",
            "sink=speakers source=microphone latency_msec=20 rate=48000 remix=false "
            "adjust_time=2",
        )
    ]
    assert hass.states.get(ENTITY).state == "on"
    await switch(hass, "turn_off")
    assert pulse.unloaded == [2]
    assert hass.states.get(ENTITY).state == "off"


async def test_without_extra_options_the_arguments_match_core(hass, pulse):
    await setup(hass, {"switch": PLATFORM})
    await switch(hass, "turn_on")
    assert pulse.loaded == [("module-loopback", "sink=speakers source=microphone")]


async def test_an_already_loaded_module_is_picked_up_as_on(hass, pulse):
    pulse.add("module-loopback", "sink=speakers source=microphone")
    await setup(hass)
    assert hass.states.get(ENTITY).state == "on"
    await switch(hass, "turn_on")
    assert pulse.loaded == []


async def test_turning_off_after_a_restart_leaves_other_modules_alone(hass, pulse):
    await setup(hass)
    await switch(hass, "turn_on")
    assert hass.states.get(ENTITY).state == "on"

    # PulseAudio restarts and a sound card gets the index the loopback had.
    pulse.restart()
    pulse.add("module-alsa-card", "device_id=0")
    await switch(hass, "turn_off")

    assert pulse.unloaded == []
    assert "module-alsa-card" in pulse.names()
    assert hass.states.get(ENTITY).state == "off"


async def test_a_missing_sink_is_reported_and_nothing_is_loaded(hass, pulse):
    await setup(hass, {"switch": {**PLATFORM, "sink_name": "nowhere"}})
    with pytest.raises(HomeAssistantError, match="does not exist"):
        await switch(hass, "turn_on")
    assert pulse.loaded == []


@pytest.mark.parametrize(
    "options",
    [
        {"name": "paloop"},
        {**PLATFORM, "module_args": {"use_volume_sharing": False}},
        {**PLATFORM, "module_args": {"sink": "speakers"}},
        {**PLATFORM, "latency_msec": 20.5},
        {**PLATFORM, "rate": 1000},
    ],
)
async def test_an_invalid_configuration_is_rejected(hass, pulse, options):
    await async_setup_component(
        hass, "switch", {"switch": {"platform": "pulseaudio_loopback", **options}}
    )
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY) is None
    assert pulse.loaded == []
