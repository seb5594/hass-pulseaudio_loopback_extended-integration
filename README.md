# PulseAudio Loopback Extended for Home Assistant

**Version 1.0.0** · [Changelog](CHANGELOG.md) · [Download release ZIPs](https://github.com/seb5594/hass-pulseaudio_loopback_extended-integration/releases/latest)

Releases include `pulseaudio_loopback.zip` for HACS and
`pulseaudio_loopback-1.0.0-manual.zip` for manual installation. Extract the manual
ZIP into your Home Assistant configuration directory; it already contains
`custom_components/pulseaudio_loopback/`. `SHA256SUMS.txt` lets you verify both
downloads. HACS selects its ZIP automatically.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/seb5594/hass-pulseaudio_loopback_extended-integration)](https://github.com/seb5594/hass-pulseaudio_loopback_extended-integration/releases)

This is a custom component for Home Assistant that extends the original [PulseAudio Loopback integration](https://www.home-assistant.io/integrations/pulseaudio_loopback/) by adding advanced audio routing parameters. 

It is designed for advanced audio setups where precise control over the PulseAudio `module-loopback` behavior is necessary. With this extension, you can easily match sample rates for bit-perfect audio, disable remixing for surround sound, prevent stream moving, or pass custom arguments directly to the PulseAudio daemon.

## 🚀 Features
- Includes **all features** of the official Home Assistant Core component.
- **`source_dont_move` & `sink_dont_move`**: Prevent PulseAudio from automatically moving the loopback streams to a fallback device when the current one disconnects.
- **`rate`**: Define the sample rate (e.g., `48000`, `44100`).
- **`channels`**: Specify the exact amount of audio channels (e.g., `2` for Stereo, `6` for 5.1 Surround).
- **`remix`**: Toggle the channel remixing behavior.
- **`module_args`**: Pass any arbitrary arguments directly to the module (e.g., `use_volume_sharing: false`).

---

## 🛠️️ Installation

### Method 1: HACS (Recommended)
1. Open HACS in your Home Assistant instance.
2. Go to **Integrations** -> click the three dots in the top right -> **Custom repositories**.
3. Add `https://github.com/seb5594/hass-pulseaudio_loopback_extended-integration` and select **Integration** as the category.
4. Click **Download** on the newly added repository.
5. Restart Home Assistant.

### Method 2: Manual Installation
1. Download the latest release from this repository.
2. Extract the archive and copy the `custom_components/pulseaudio_loopback` folder into your Home Assistant `config/custom_components/` directory.
3. Restart Home Assistant.

---

## ⚙️ Configuration

Add the extended loopback switch to your `configuration.yaml`. 

### Example Configuration

```yaml
switch:
  - platform: pulseaudio_loopback

    # Standard Core Parameters
    name: PulseAudio USB Soundcard Toslink Loopback
    source_name: alsa_input.usb-0d8c_USB_Sound_Device-00.iec958-stereo
    sink_name: alsa_output.pci-0000_04_00.1.hdmi-stereo

    # Extended Parameters
    #adjust_time: 0
    latency_msec: 5

    source_dont_move: true
    sink_dont_move: true
    rate: 48000
    channels: 2 # e.g., 6 for 5.1 audio
    remix: false
    
    # Arbitrary Module Arguments
    module_args:
      use_volume_sharing: false
```

### Configuration Variables

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `platform` | string | **Yes** | | Must be exactly `pulseaudio_loopback`. |
| `name` | string | No | *PulseAudio Loopback* | The name of the switch entity in Home Assistant. |
| `source_name` | string | No | | The exact name of the PulseAudio source to loop audio *from*. |
| `sink_name` | string | No | | The exact name of the PulseAudio sink to loop audio *to*. |
| `source_dont_move` | boolean | No | `false` | **[NEW]** If set to `true`, prevents PulseAudio from automatically moving the source stream to another device. |
| `sink_dont_move` | boolean | No | `false` | **[NEW]** If set to `true`, prevents PulseAudio from automatically moving the sink stream to another device. |
| `adjust_time` | integer | No | | Time in seconds to adjust the latency. |
| `latency_msec` | integer | No | | Fixed latency in milliseconds. |
| `rate` | integer | No | | **[NEW]** The sample rate to use for the loopback (e.g., `44100`, `48000`, `96000`). |
| `channels` | integer | No | | **[NEW]** Number of audio channels (e.g., `2` for Stereo, `6` for 5.1). |
| `remix` | boolean | No | `true` | **[NEW]** Whether to remix channels. Set to `false` to prevent unwanted upmixing/downmixing. |
| `module_args` | list/dict | No | | **[NEW]** Dictionary of additional raw arguments passed to `module-loopback`. For boolean values, use `true` or `false` (e.g., `use_volume_sharing: false`). |

> **Note on `module_args`:** Be careful when using additional module arguments. Ensure your underlying PulseAudio or PipeWire server supports the specific parameters you are passing, otherwise the module might fail to load.

---

## 🤝 Acknowledgments & Contribution
This custom integration is based entirely on the [original Home Assistant Core implementation](https://github.com/home-assistant/core/tree/dev/homeassistant/components/pulseaudio_loopback). 

The ultimate goal of this repository is to test these features in the wild and eventually contribute them back via a Pull Request to Home Assistant Core. Feel free to open issues or contribute!
