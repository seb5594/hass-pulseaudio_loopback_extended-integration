# Changelog

## 1.0.0

First release.

- Extends the core PulseAudio loopback switch with `latency_msec`, `adjust_time`,
  `rate`, `channels`, `remix`, `format`, `source_dont_move` and `sink_dont_move`.
- `module_args` takes every other `module-loopback` argument, for example
  `max_latency_msec`, `channel_map` or stream properties (also as a YAML mapping).
- Every argument is checked against PulseAudio's own limits while the configuration
  is read, so typos and out-of-range values never reach the audio server. Values with
  spaces or quotes are quoted correctly.
- Leaves the rest of the audio setup alone: a switch only unloads a loopback it has
  just found and verified on the server, never a remembered module number. That
  number can belong to a sound card after PulseAudio restarts.
- Recognises its loopback by the exact sink and source, so a similar one
  (`speakers_rear` for `speakers`) is left alone.
- Before loading, sink and source must exist, and a loopback from a sink's monitor
  into the same sink is refused. A loopback that is already running is taken over
  instead of loaded twice.
- Switches sharing one server take turns instead of using the same connection at
  once.
- Without extra options the module arguments are exactly the ones the core
  integration uses.
- Errors show up in Home Assistant with the reason.
- Works on Home Assistant 2022.4 and newer (Python 3.9+); the tests run inside real
  Home Assistant cores from 2022.4.7 to 2026.9.4.
- HACS ready, with separate HACS and manual-installation ZIPs and SHA-256 checksums.
