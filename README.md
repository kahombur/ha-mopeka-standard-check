# Mopeka Standard Check — Home Assistant integration

A custom Home Assistant integration for **Mopeka _Standard_ "Check"** Bluetooth
propane/LPG tank sensors (e.g. Walmart `8015004` / Ace `024-1011`).

Home Assistant's built-in [`mopeka`](https://www.home-assistant.io/integrations/mopeka/)
integration only decodes the **Pro** family. The **Standard** sensor is a
different device entirely — a TI chip advertising service UUID `0xADA0` that
broadcasts _raw ultrasonic echo data_, so the client has to run the
peak-detection + speed-of-sound math itself. This integration does that,
using Home Assistant's existing Bluetooth stack (a local Bluetooth adapter or
an [ESPHome Bluetooth proxy](https://esphome.io/components/bluetooth_proxy.html))
— **no extra hardware or ESP32 required.**

The decoding is a Python port of ESPHome's excellent
[`mopeka_std_check`](https://esphome.io/components/sensor/mopeka_std_check/)
component.

## Features

Per sensor:

| Entity | Description |
| --- | --- |
| `tank_level_percent` | Fill level (%) from the selected tank size — Mopeka-app style |
| `tank_level` | Raw liquid-column distance (mm) |
| `temperature` | Sensor temperature |
| `battery` | Battery % (CR2032 curve) |
| `reading_quality` | Strength/confidence of the strongest echo |
| `battery_voltage` | Battery voltage (disabled by default) |
| `signal_strength` | BLE RSSI (disabled by default) |

**Tank-size selector** — pick your tank when adding the sensor, or change it
later via the device's **Configure** button:

- 20 / 30 / 40 lb vertical (US)
- 6 / 11 / 14 kg (Europe)
- Custom

## Install

### HACS (recommended)

1. HACS → ⋮ → **Custom repositories**.
2. Add `https://github.com/kahombur/ha-mopeka-standard-check`, category **Integration**.
3. Install **Mopeka Standard Check**, then restart Home Assistant.

### Manual

Copy `custom_components/mopeka_std` into your Home Assistant `config/custom_components/`
directory and restart.

## Setup

1. Install a CR2032 battery in the sensor and **press its sync button** so it
   broadcasts.
2. Within Bluetooth range of a HA Bluetooth adapter/proxy, HA will
   **auto-discover** it under **Settings → Devices & Services**.
3. Click **Add**, choose your **tank size**, and submit.
4. Mount the sensor on the bottom-center of the tank per Mopeka's instructions.

## Notes

- Verified against real hardware — the reported level matches the Mopeka Check
  phone app.
- If your reading is consistently off, the propane/butane mix coefficient
  (`PROPANE_BUTANE_MIX` in `parser.py`, default `1.0` = pure propane) can be
  tuned.
- Supported hardware types: Standard, Standard-Alt, XL, and eTrailer.

## Credits & license

Decoding algorithm ported from [ESPHome](https://github.com/esphome/esphome)'s
`mopeka_std_check` component. Integration structure follows Home Assistant's
built-in `mopeka` integration.

Licensed under **GPL-3.0** (compatible with the ESPHome-derived algorithm). See
[`LICENSE`](LICENSE).

Not affiliated with or endorsed by Mopeka Products LLC.
