# Changelog

## Unreleased

- Works on Home Assistant 2022.4 and newer (Python 3.9+); the tests run inside real Home Assistant cores from 2022.4.7 to 2026.9.4.
- Fix: turning a switch off after PulseAudio had restarted could unload an unrelated
  module that had inherited the loopback's old number, such as a sound card, and with
  it the interfaces. A switch now only unloads a loopback it has just found and
  verified on the server.
- Fix: a loopback with a similar name (`speakers_rear` for `speakers`) was mistaken
  for the switch's own and could be unloaded by it.
- Fix: switches sharing a server could use the same connection at the same time,
  which could crash the audio client inside Home Assistant.
- `module_args` only accepts real `module-loopback` arguments, and every value is
  checked against PulseAudio's own limits while the configuration is read.
  `use_volume_sharing` from the old README example was never a loopback argument and
  is now reported instead of silently failing to load.
- Values with spaces or quotes are quoted correctly; stream properties can be written
  as a mapping.
- Before loading, sink and source must exist, and a loopback from a sink's monitor
  into the same sink is refused.
- An already running identical loopback is taken over instead of loaded twice.
- `source_dont_move` and `sink_dont_move` are only sent when configured, so without
  extra options the module arguments are exactly the ones the core integration uses.
- Errors show up in Home Assistant with the reason instead of a bare PulseAudio
  exception.

## 1.0.0

- Extend PulseAudio loopback switches with configurable latency, rate, channels,
  remixing, stream movement, format, and additional module arguments.
- Add HACS validation and Python checks before every release.
- Provide separate HACS and manual-installation ZIPs with SHA-256 checksums.
- Retain compatibility with older Home Assistant schema validators and Python 3.11.
