"""Test PulseAudio module arguments and switch state without audio hardware."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


class PulseError(Exception):
    """Mock the PulseAudio transport exception."""


tree = ast.parse(Path("custom_components/pulseaudio_loopback/switch.py").read_text())
switch = next(node for node in tree.body if isinstance(node, ast.ClassDef))
namespace = {
    "Any": object, "Pulse": object, "PulseError": PulseError, "SwitchEntity": object,
    "override": lambda method: method, "_LOGGER": Mock(),
    "IGNORED_SWITCH_WARN": "already set",
}
# Load the actual switch class; Home Assistant schema setup is validated by HACS.
exec(compile(ast.Module(body=[switch], type_ignores=[]), "switch.py", "exec"), namespace)
Switch = namespace["PALoopbackSwitch"]


class SwitchTests(unittest.TestCase):
    def setUp(self):
        self.server = Mock()
        self.server.module_load.return_value = 42
        self.switch = Switch("Test", self.server, "sink", "source",
                             {"remix": False, "rate": 48000, "latency_msec": 20.0})

    def test_arguments_preserve_types(self):
        self.assertEqual(self.switch._build_module_arguments(),
                         "sink=sink source=source remix=false rate=48000 latency_msec=20")

    def test_on_off_are_idempotent(self):
        self.switch.turn_on()
        self.switch.turn_on()
        self.server.module_load.assert_called_once()
        self.assertTrue(self.switch.is_on)
        self.switch.turn_off()
        self.switch.turn_off()
        self.server.module_unload.assert_called_once_with(42)
        self.assertFalse(self.switch.is_on)

    def test_update_and_transport_failure(self):
        self.server.module_list.return_value = [SimpleNamespace(
            name="module-loopback", argument="sink=sink source=source", index=17)]
        self.switch.update()
        self.assertTrue(self.switch.is_on)
        self.server.connect.side_effect = PulseError()
        self.switch.update()
        self.assertFalse(self.switch.is_on)

    def test_load_failure_does_not_leave_on_state(self):
        self.server.module_load.side_effect = PulseError()
        with self.assertRaises(PulseError):
            self.switch.turn_on()
        self.assertFalse(self.switch.is_on)
