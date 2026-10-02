# Changelog

## Unreleased

- Works on Home Assistant 2022.4 and newer (Python 3.9+); the tests run inside real Home Assistant cores from 2022.4.7 to 2026.9.4.

## 1.0.0

- Extend PulseAudio loopback switches with configurable latency, rate, channels,
  remixing, stream movement, format, and additional module arguments.
- Add HACS validation and Python checks before every release.
- Provide separate HACS and manual-installation ZIPs with SHA-256 checksums.
- Retain compatibility with older Home Assistant schema validators and Python 3.11.
