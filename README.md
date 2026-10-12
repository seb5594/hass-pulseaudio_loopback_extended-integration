# PulseAudio Loopback Extended for Home Assistant

<!-- badges:begin (generated from project metadata) -->
[![HACS](https://img.shields.io/static/v1?label=HACS&message=Add%20integration&color=41BDF5&style=flat&logo=homeassistantcommunitystore&logoColor=white)](https://my.home-assistant.io/redirect/hacs_repository/?owner=seb5594&repository=hass-pulseaudio_loopback_extended-integration&category=integration)<br>
![home assistant](https://img.shields.io/static/v1?label=home%20assistant&message=%E2%89%A5%202022.4.0&color=1877A5&style=flat) [![version](https://img.shields.io/static/v1?label=version&message=1.0.0&color=1877A5&style=flat)](https://github.com/seb5594/hass-pulseaudio_loopback_extended-integration/releases) [![released](https://img.shields.io/github/release-date-pre/seb5594/hass-pulseaudio_loopback_extended-integration?label=released&style=flat)](https://github.com/seb5594/hass-pulseaudio_loopback_extended-integration/releases) [![checks](https://img.shields.io/github/actions/workflow/status/seb5594/hass-pulseaudio_loopback_extended-integration/ci.yml?branch=main&label=checks&style=flat)](https://github.com/seb5594/hass-pulseaudio_loopback_extended-integration/actions/workflows/ci.yml) [![HA releases](https://img.shields.io/github/actions/workflow/status/seb5594/hass-pulseaudio_loopback_extended-integration/compat.yml?branch=main&label=HA%20releases&style=flat)](https://github.com/seb5594/hass-pulseaudio_loopback_extended-integration/actions/workflows/compat.yml)<br>
[![downloads](https://img.shields.io/github/downloads/seb5594/hass-pulseaudio_loopback_extended-integration/total?label=downloads&style=flat)](https://github.com/seb5594/hass-pulseaudio_loopback_extended-integration/releases) ![ZIP size](https://img.shields.io/static/v1?label=ZIP%20size&message=9.8%20KiB&color=157F71&style=flat) ![tests](https://img.shields.io/static/v1?label=tests&message=20%20passed&color=2F855A&style=flat)<br>
[![updated](https://img.shields.io/github/last-commit/seb5594/hass-pulseaudio_loopback_extended-integration?label=updated&style=flat)](https://github.com/seb5594/hass-pulseaudio_loopback_extended-integration/commits/main)
<!-- badges:end -->

This is a custom component for Home Assistant that extends the original [PulseAudio Loopback integration](https://www.home-assistant.io/integrations/pulseaudio_loopback/) by adding advanced audio routing parameters. 

It is designed for advanced audio setups where precise control over the PulseAudio `module-loopback` behavior is necessary. With this extension, you can easily match sample rates for bit-perfect audio, disable remixing for surround sound, prevent stream moving, or pass custom arguments directly to the PulseAudio daemon.

## 🚀 Features
- Includes **all features** of the official Home Assistant Core component.
- **`source_dont_move` & `sink_dont_move`**: Prevent PulseAudio from automatically moving the loopback streams to a fallback device when the current one disconnects.
- **`rate`**: Define the sample rate (e.g., `48000`, `44100`).
- **`channels`**: Specify the exact amount of audio channels (e.g., `2` for Stereo, `6` for 5.1 Surround).
- **`remix`**: Toggle the channel remixing behavior.
- **`format`**: Pin the sample format (e.g., `s16le`, `s24le`, `float32le`).
- **`module_args`**: Pass any other `module-loopback` argument, like `max_latency_msec`, `channel_map` or stream properties. Typos and out-of-range values are caught when Home Assistant checks the configuration, not by the audio server.
- **Leaves the rest of your audio setup alone**, even when PulseAudio restarts underneath it. See [Safety](#%EF%B8%8F-safety).

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

    # Any other module-loopback argument
    module_args:
      max_latency_msec: 200
      sink_input_properties:
        media.name: Toslink loopback
```

The names of your sinks and sources are listed by `pactl list short sinks` and `pactl list short sources`.

### Configuration Variables

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `platform` | string | **Yes** | | Must be exactly `pulseaudio_loopback`. |
| `name` | string | No | `paloopback` | The name of the switch entity in Home Assistant. |
| `source_name` | string | **Yes** | | The exact name of the PulseAudio source to loop audio *from*. |
| `sink_name` | string | **Yes** | | The exact name of the PulseAudio sink to loop audio *to*. |
| `host` | string | No | | Address of a remote PulseAudio server. Leave it out for the local one, e.g. the audio server of Home Assistant OS. |
| `port` | integer | No | `4713` | Port of the remote PulseAudio server. |
| `source_dont_move` | boolean | No | `false` | **[NEW]** If set to `true`, prevents PulseAudio from automatically moving the source stream to another device. |
| `sink_dont_move` | boolean | No | `false` | **[NEW]** If set to `true`, prevents PulseAudio from automatically moving the sink stream to another device. |
| `adjust_time` | number | No | `1` | How often the latency gets readjusted, in seconds. `0` turns it off, otherwise at least `0.1`. |
| `latency_msec` | integer | No | `200` | Target latency in milliseconds, `1` to `30000`. |
| `rate` | integer | No | | **[NEW]** The sample rate to use for the loopback, `4000` to `768000` (e.g., `44100`, `48000`, `96000`). |
| `channels` | integer | No | | **[NEW]** Number of audio channels, `1` to `32` (e.g., `2` for Stereo, `6` for 5.1). |
| `remix` | boolean | No | `true` | **[NEW]** Whether to remix channels. Set to `false` to prevent unwanted upmixing/downmixing. |
| `format` | string | No | | **[NEW]** Sample format, e.g. `s16le`, `s24le`, `s32le` or `float32le`. |
| `module_args` | mapping | No | | **[NEW]** Further `module-loopback` arguments, see below. |

Options without a default are left to PulseAudio, which then follows the source.

### `module_args`

Everything `module-loopback` understands can go in here, including the options above (if both are set, `module_args` wins):

| Argument | Accepted values |
|----------|-----------------|
| `max_latency_msec` | Upper latency limit in milliseconds, `0` means no limit. |
| `fast_adjust_threshold_msec` | `0` (off) or at least `100`. |
| `adjust_threshold_usec` | `1` to `10000`. |
| `log_interval` | Seconds between latency log lines, `0` turns logging off. |
| `channel_map` | Positions like `front-left,front-right` (a YAML list works too) or a name like `stereo`. |
| `sink_input_properties`, `source_output_properties` | Stream properties as a mapping (recommended) or as PulseAudio text such as `media.role=music`. |

`sink` and `source` are not allowed here, they come from `sink_name` and `source_name`. Anything else is rejected with a message that names the offending entry, so it never reaches the audio server. A few arguments need a recent PulseAudio; Home Assistant OS ships PulseAudio 17, which knows all of them.

A switch recognises its loopback by sink and source, just like the core integration. If you change other options while the loopback is running, switch it off and on again to apply them.

## 🛡️ Safety

A loopback switch shares the audio server with everything else, so it is careful about what it touches:

- It only ever unloads a module it has just found on the server and verified as a `module-loopback` with exactly its sink and source. PulseAudio numbers its modules anew after every restart; a remembered number could by then belong to a sound card, so the switch never acts on one.
- Before loading, the sink and the source have to exist. A source that is the monitor of the target sink is refused, because the loopback would feed the sink back into itself.
- A loopback that is already running is taken over instead of loaded a second time.
- Switches talking to the same server take turns, so two automations firing at the same moment cannot pull the connection away from each other.

If something goes wrong anyway, the error shows up in Home Assistant with the reason, for example `Could not turn on TV: sink hdmi_out does not exist on the PulseAudio server`.

---

## 🤝 Acknowledgments & Contribution
This custom integration is based entirely on the [original Home Assistant Core implementation](https://github.com/home-assistant/core/tree/dev/homeassistant/components/pulseaudio_loopback). 

The ultimate goal of this repository is to test these features in the wild and eventually contribute them back via a Pull Request to Home Assistant Core. Feel free to open issues or contribute! See the [changelog](CHANGELOG.md) for what changed in each release.

<!-- support:begin (generated, shared text) -->
## Say thanks

All my projects are built in my spare time, just for the fun of it. Still, they take a lot of time and care, and many of the smart home gadgets I buy end up here because I want to make them cloud-free and smart-home ready. Every bit of support means a lot to me.

If my work helped you or turned out to be useful, show your appreciation with a hot drink for my next sleepless night.

[![Buy Me a Coffee](https://img.shields.io/static/v1?label=Support&message=Buy%20Me%20a%20Coffee&color=FFDD00&logo=buy-me-a-coffee&logoColor=black&style=for-the-badge)](https://buymeacoffee.com/seb5594) [![PayPal](https://img.shields.io/static/v1?label=Support&message=PayPal&color=0070BA&logo=paypal&logoColor=white&style=for-the-badge)](https://www.paypal.com/donate/?hosted_button_id=QMQPNRENXDN26)
<!-- support:end -->

<!-- license:begin (generated from the license file) -->
## License

[![license](https://img.shields.io/static/v1?label=license&message=Apache-2.0&color=5B6770&style=flat)](LICENSE.md)

Published under the [Apache License 2.0](LICENSE.md).
<!-- license:end -->
