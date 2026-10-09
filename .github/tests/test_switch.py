"""Argument handling and module safety, tested without Home Assistant or audio hardware.

Run from the repository root with either `python -m pytest .github/tests` or
`python -m unittest discover -s .github/tests`. Only the standard library is
needed; pulsectl is replaced by a small stand-in when it is not installed.
"""

from pathlib import Path
import sys
import threading
import types
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

try:
    import pulsectl
except ImportError:  # The tests only need pulsectl's exception classes.
    pulsectl = types.ModuleType("pulsectl")
    pulsectl.PulseError = type("PulseError", (Exception,), {})
    pulsectl.PulseIndexError = type("PulseIndexError", (pulsectl.PulseError,), {})
    pulsectl.PulseOperationFailed = type(
        "PulseOperationFailed", (pulsectl.PulseError,), {}
    )
    pulsectl.Pulse = object
    sys.modules["pulsectl"] = pulsectl

from custom_components.pulseaudio_loopback import arguments  # noqa: E402
from custom_components.pulseaudio_loopback.loopback import (  # noqa: E402
    Loopback,
    LoopbackRefused,
    PulseServer,
)

# The modules a freshly started Home Assistant OS audio server loads first.
BASE_MODULES = (
    ("module-device-restore", ""),
    ("module-udev-detect", ""),
    ("module-alsa-card", "device_id=0 name=usb card_name=alsa_card.usb"),
    (
        "module-native-protocol-unix",
        "auth-anonymous=1 socket=/data/external/pulse.sock",
    ),
)


class FakePulse:
    """A PulseAudio server that behaves like the real one where it matters here.

    Module indices count up per server run and start over after a restart,
    which is exactly what makes a remembered index dangerous.
    """

    def __init__(self, sinks=("speakers",), sources=("microphone", "speakers.monitor")):
        self.connected = None
        self.sinks = set(sinks)
        self.sources = set(sources)
        self.connections = 0
        self.unloaded = []
        self.restart()

    def restart(self):
        self.modules = []
        self._next_index = 0
        for name, argument in BASE_MODULES:
            self.add_module(name, argument)

    def add_module(self, name, argument):
        module = types.SimpleNamespace(
            index=self._next_index, name=name, argument=argument
        )
        self._next_index += 1
        self.modules.append(module)
        return module.index

    def connect(self):
        self.connections += 1
        self.connected = True

    def module_list(self):
        return list(self.modules)

    def module_load(self, name, args):
        return self.add_module(name, args)

    def module_unload(self, index):
        if not any(module.index == index for module in self.modules):
            raise pulsectl.PulseOperationFailed(index)
        self.unloaded.append(index)
        self.modules = [module for module in self.modules if module.index != index]

    def get_sink_by_name(self, name):
        if name not in self.sinks:
            raise pulsectl.PulseIndexError(name)
        return types.SimpleNamespace(name=name)

    def get_source_by_name(self, name):
        if name not in self.sources:
            raise pulsectl.PulseIndexError(name)
        monitor_of = name[: -len(".monitor")] if name.endswith(".monitor") else None
        return types.SimpleNamespace(name=name, monitor_of_sink_name=monitor_of)

    def module_names(self):
        return [module.name for module in self.modules]


class ArgumentFormattingTests(unittest.TestCase):
    def test_plain_values_stay_untouched(self):
        self.assertEqual(
            arguments.format_module_argument(
                {"sink": "speakers", "source": "microphone", "rate": 48000}
            ),
            "sink=speakers source=microphone rate=48000",
        )

    def test_numbers_and_booleans_are_written_like_pactl(self):
        self.assertEqual(
            arguments.format_module_argument(
                {"remix": False, "latency_msec": 20.0, "adjust_time": 0.5}
            ),
            "remix=false latency_msec=20 adjust_time=0.5",
        )

    def test_blanks_and_quotes_are_quoted_and_round_trip(self):
        name = 'usb "mic" \\ in'
        text = arguments.format_module_argument({"source": name, "sink": "x"})
        self.assertEqual(text, 'source="usb \\"mic\\" \\\\ in" sink=x')
        self.assertEqual(arguments.parse_module_argument(text)["source"], name)

    def test_property_mapping_survives_both_parsers(self):
        value = 'Seb\'s "TV" \\ loop'
        text = arguments.format_module_argument(
            {"sink_input_properties": {"media.name": value, "media.role": "music"}}
        )
        # module-loopback reads the raw text between the outer quotes.
        raw = text[len("sink_input_properties='") : -1]
        self.assertEqual(
            arguments.parse_property_list(raw),
            {"media.name": value, "media.role": "music"},
        )


class ArgumentParsingTests(unittest.TestCase):
    def test_reads_quotes_escapes_and_empty_values(self):
        self.assertEqual(
            arguments.parse_module_argument(
                "sink=a\\ b source='x y' latency_msec= remix=\"true\""
            ),
            {"sink": "a b", "source": "x y", "latency_msec": "", "remix": "true"},
        )

    def test_broken_text_yields_what_could_be_read(self):
        self.assertEqual(
            arguments.parse_module_argument('sink=a source="b'), {"sink": "a"}
        )
        self.assertEqual(arguments.parse_module_argument(None), {})

    def test_property_text_is_read_like_pulseaudio(self):
        self.assertEqual(
            arguments.parse_property_list(
                "media.role = music  device.description='TV room'"
            ),
            {"media.role": "music", "device.description": "TV room"},
        )
        for broken in ("media.role", "a=", "a='open", "a=hex:00"):
            with self.subTest(broken), self.assertRaises(ValueError):
                arguments.parse_property_list(broken)


class ArgumentValidationTests(unittest.TestCase):
    def test_accepts_what_pulseaudio_accepts(self):
        self.assertEqual(
            arguments.validate_arguments(
                {
                    "latency_msec": "20",
                    "adjust_time": 0,
                    "fast_adjust_threshold_msec": 0,
                    "format": "S24LE",
                    "channel_map": ["front-left", "front-right"],
                    "remix": "off",
                    "sink_input_properties": "media.role=music",
                }
            ),
            {
                "latency_msec": 20,
                "adjust_time": 0.0,
                "fast_adjust_threshold_msec": 0,
                "format": "s24le",
                "channel_map": "front-left,front-right",
                "remix": False,
                "sink_input_properties": {"media.role": "music"},
            },
        )

    def test_rejects_what_pulseaudio_would_refuse(self):
        rejected = {
            "latency_msec": [0, 30001, 20.5, "fast", True],
            "adjust_time": [0.05, -1, float("nan"), float("inf")],
            "fast_adjust_threshold_msec": [50],
            "adjust_threshold_usec": [0, 10001],
            "rate": [3999, 768001],
            "channels": [0, 33],
            "format": ["s17le", ""],
            "channel_map": ["front left; rear", ""],
            "remix": ["maybe", None],
            "sink_input_properties": ["", {}, {"bad key": "x"}, "media.role"],
        }
        for name, values in rejected.items():
            for value in values:
                with (
                    self.subTest(name=name, value=value),
                    self.assertRaises((TypeError, ValueError)),
                ):
                    arguments.validate_argument(name, value)

    def test_unknown_and_reserved_names_are_explained(self):
        with self.assertRaisesRegex(ValueError, "not a module-loopback argument"):
            arguments.validate_arguments({"use_volume_sharing": False})
        with self.assertRaisesRegex(ValueError, "sink_name option"):
            arguments.validate_arguments({"sink": "speakers"})


class LoopbackSafetyTests(unittest.TestCase):
    def setUp(self):
        self.pulse = FakePulse()
        self.server = PulseServer(self.pulse)
        self.loopback = Loopback("speakers", "microphone", {"latency_msec": 20})

    def test_load_find_and_unload(self):
        with self.server.session() as session:
            index = session.load(self.loopback)
            self.assertEqual(session.find(self.loopback), index)
            self.assertEqual(session.unload(self.loopback), 1)
            self.assertIsNone(session.find(self.loopback))
        self.assertEqual(self.pulse.module_names(), [name for name, _ in BASE_MODULES])

    def test_restart_never_unloads_a_reused_index(self):
        with self.server.session() as session:
            index = session.load(self.loopback)

        # After a restart the old loopback index belongs to another module.
        self.pulse.restart()
        self.pulse.add_module("module-alsa-card", "device_id=1 name=hdmi")
        self.assertEqual(self.pulse.modules[index].name, "module-alsa-card")

        with self.server.session() as session:
            self.assertEqual(session.unload(self.loopback), 0)
        self.assertEqual(self.pulse.unloaded, [])

    def test_only_exact_sink_and_source_count(self):
        foreign = (
            "sink=speakers_rear source=microphone",
            "sink=speakers source=microphone_2",
            "source=microphone",
        )
        for argument in foreign:
            self.pulse.add_module("module-loopback", argument)
        self.pulse.add_module("module-null-sink", "sink=speakers source=microphone")

        with self.server.session() as session:
            self.assertIsNone(session.find(self.loopback))
            self.assertEqual(session.unload(self.loopback), 0)
        self.assertEqual(self.pulse.unloaded, [])

    def test_quoted_arguments_of_other_tools_are_recognized(self):
        index = self.pulse.add_module(
            "module-loopback", "source='microphone' sink=\"speakers\" rate=44100"
        )
        with self.server.session() as session:
            self.assertEqual(session.find(self.loopback), index)

    def test_unload_removes_duplicates_and_tolerates_vanished_modules(self):
        first = self.pulse.add_module(
            "module-loopback", "sink=speakers source=microphone"
        )
        second = self.pulse.add_module(
            "module-loopback", "sink=speakers source=microphone"
        )
        real_unload = self.pulse.module_unload

        def unload_racing_with_pulseaudio(index):
            if index == first:
                # The module unloads itself right before we get to it.
                self.pulse.modules = [m for m in self.pulse.modules if m.index != index]
            real_unload(index)

        self.pulse.module_unload = unload_racing_with_pulseaudio
        with self.server.session() as session:
            self.assertEqual(session.unload(self.loopback), 2)
            self.assertIsNone(session.find(self.loopback))
        self.assertEqual(self.pulse.unloaded, [second])

    def test_unload_failure_of_a_present_module_is_reported(self):
        self.pulse.add_module("module-loopback", "sink=speakers source=microphone")

        def refuse(index):
            raise pulsectl.PulseOperationFailed(index)

        self.pulse.module_unload = refuse
        with (
            self.server.session() as session,
            self.assertRaises(pulsectl.PulseOperationFailed),
        ):
            session.unload(self.loopback)

    def test_missing_devices_and_feedback_are_refused_before_loading(self):
        cases = {
            "does not exist": Loopback("nowhere", "microphone"),
            "monitor of sink": Loopback("speakers", "speakers.monitor"),
        }
        for reason, loopback in cases.items():
            with self.subTest(reason), self.server.session() as session:
                with self.assertRaisesRegex(LoopbackRefused, reason):
                    session.load(loopback)
        self.assertNotIn("module-loopback", self.pulse.module_names())

    def test_every_session_connects_afresh(self):
        for _ in range(3):
            with self.server.session():
                pass
        self.assertEqual(self.pulse.connections, 3)

    def test_sessions_never_overlap(self):
        inside = threading.Event()
        release = threading.Event()
        second_entered = threading.Event()

        def first():
            with self.server.session():
                inside.set()
                release.wait(5)

        def second():
            with self.server.session():
                second_entered.set()

        holder = threading.Thread(target=first)
        holder.start()
        inside.wait(5)
        waiter = threading.Thread(target=second)
        waiter.start()
        self.assertFalse(second_entered.wait(0.2))
        release.set()
        holder.join(5)
        waiter.join(5)
        self.assertTrue(second_entered.is_set())

    def test_arguments_are_frozen(self):
        settings = {"latency_msec": 20}
        loopback = Loopback("speakers", "microphone", settings)
        settings["latency_msec"] = 5
        self.assertEqual(
            loopback.module_argument, "sink=speakers source=microphone latency_msec=20"
        )
        with self.assertRaises(TypeError):
            loopback.arguments["rate"] = 48000


if __name__ == "__main__":
    unittest.main()
