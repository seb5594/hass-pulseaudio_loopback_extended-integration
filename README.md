# PulseAudio Loopback Extended for Home Assistant

<!-- badges:begin (generated from project metadata) -->
[![version](https://img.shields.io/static/v1?label=version&message=1.0.0&color=1877A5&style=flat)](https://github.com/seb5594/hass-pulseaudio_loopback_extended-integration/releases) [![released](https://img.shields.io/github/release-date-pre/seb5594/hass-pulseaudio_loopback_extended-integration?label=released&style=flat)](https://github.com/seb5594/hass-pulseaudio_loopback_extended-integration/releases) [![checks](https://img.shields.io/github/actions/workflow/status/seb5594/hass-pulseaudio_loopback_extended-integration/ci.yml?branch=main&label=checks&style=flat)](https://github.com/seb5594/hass-pulseaudio_loopback_extended-integration/actions/workflows/ci.yml)

[![stars](https://img.shields.io/github/stars/seb5594/hass-pulseaudio_loopback_extended-integration?label=stars&style=flat)](https://github.com/seb5594/hass-pulseaudio_loopback_extended-integration/stargazers) [![issues](https://img.shields.io/github/issues/seb5594/hass-pulseaudio_loopback_extended-integration?label=issues&style=flat)](https://github.com/seb5594/hass-pulseaudio_loopback_extended-integration/issues) [![updated](https://img.shields.io/github/last-commit/seb5594/hass-pulseaudio_loopback_extended-integration?label=updated&style=flat)](https://github.com/seb5594/hass-pulseaudio_loopback_extended-integration/commits/main)

[![downloads](https://img.shields.io/github/downloads/seb5594/hass-pulseaudio_loopback_extended-integration/total?label=downloads&style=flat)](https://github.com/seb5594/hass-pulseaudio_loopback_extended-integration/releases) [![latest release](https://img.shields.io/github/downloads/seb5594/hass-pulseaudio_loopback_extended-integration/latest/total?label=latest%20release&style=flat)](https://github.com/seb5594/hass-pulseaudio_loopback_extended-integration/releases/latest)

![home assistant](https://img.shields.io/static/v1?label=home%20assistant&message=%E2%89%A5%202023.12.0&color=1877A5&style=flat) ![stage](https://img.shields.io/static/v1?label=stage&message=stable&color=2F855A&style=flat) ![type](https://img.shields.io/static/v1?label=type&message=integration&color=5B6770&style=flat) ![iot class](https://img.shields.io/static/v1?label=iot%20class&message=local%20polling&color=5B6770&style=flat) ![requirements](https://img.shields.io/static/v1?label=requirements&message=1&color=1877A5&style=flat)

![tests](https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Fseb5594%2Fhass-pulseaudio_loopback_extended-integration%2Fbadges%2Ftests.json&style=flat) ![HACS zip](https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Fseb5594%2Fhass-pulseaudio_loopback_extended-integration%2Fbadges%2Fzip-size.json&style=flat) ![last build](https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Fseb5594%2Fhass-pulseaudio_loopback_extended-integration%2Fbadges%2Flast-build.json&style=flat)

[![HACS](https://img.shields.io/static/v1?label=HACS&message=Add%20integration&color=41BDF5&style=flat&logo=homeassistantcommunitystore&logoColor=white)](https://my.home-assistant.io/redirect/hacs_repository/?owner=seb5594&repository=hass-pulseaudio_loopback_extended-integration&category=integration) [![Buy Me a Coffee](https://img.shields.io/static/v1?label=Support&message=Buy%20Me%20a%20Coffee&color=FFDD00&logo=buy-me-a-coffee&logoColor=black&style=flat)](https://buymeacoffee.com/seb5594) [![PayPal](https://img.shields.io/static/v1?label=Support&message=PayPal&color=0070BA&logo=paypal&logoColor=white&style=flat)](https://www.paypal.com/donate/?hosted_button_id=QMQPNRENXDN26)
<!-- badges:end -->

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
1. Use the **HACS** badge above to open this repository in your instance,
   or open HACS manually.
2. Go to **Integrations** -> click the three dots in the top right -> **Custom repositories**.
3. Add `https://github.com/seb5594/hass-pulseaudio_loopback_extended-integration` and select **Integration** as the category.
4. Click **Download** on the newly added repository.
5. Restart Home Assistant.

### Method 2: Manual Installation
Run this in the Home Assistant terminal (SSH or Terminal app):

```bash
cd /config
mkdir -p custom_components/pulseaudio_loopback
wget -O /tmp/pulseaudio_loopback.zip \
  https://github.com/seb5594/hass-pulseaudio_loopback_extended-integration/releases/latest/download/pulseaudio_loopback.zip
unzip -o /tmp/pulseaudio_loopback.zip -d custom_components/pulseaudio_loopback
rm /tmp/pulseaudio_loopback.zip
```

Then restart Home Assistant. `SHA256SUMS.txt` in the release lets you verify the download.

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

The ultimate goal of this repository is to test these features in the wild and eventually contribute them back via a Pull Request to Home Assistant Core. Feel free to open issues or contribute! See the [changelog](CHANGELOG.md) for what changed in each release.
