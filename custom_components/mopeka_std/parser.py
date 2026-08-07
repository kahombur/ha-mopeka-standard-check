"""Parser for Mopeka Standard Check BLE advertisements.

The Standard "Check" sensor (TI chip, service UUID 0xADA0) speaks a different
protocol from the Pro line handled by the built-in `mopeka` integration: it
broadcasts the raw ultrasonic echo data and the client must run the peak-
detection + speed-of-sound math itself. This decoder is a Python port of
ESPHome's open-source `mopeka_std_check` component.
"""

from __future__ import annotations

import logging

from bluetooth_data_tools import short_address
from bluetooth_sensor_state_data import BluetoothData
from home_assistant_bluetooth import BluetoothServiceInfo
from sensor_state_data import SensorDeviceClass, SensorLibrary, Units

_LOGGER = logging.getLogger(__name__)

# 16-bit service UUID 0xADA0 in full 128-bit form.
STD_SERVICE_UUID = "0000ada0-0000-1000-8000-00805f9b34fb"

# hardware id = manufacturer_data[1] & 0xCF
SENSOR_TYPES = {
    0x02: "Standard",
    0x03: "XL",
    0x44: "Standard",  # STANDARD_ALT
    0x46: "eTrailer",
}

# Manufacturer payload is a 19-byte packed struct:
#   [0] data_0, [1] data_1 (hw id), [2] raw_voltage,
#   [3] raw_temp(6) | slow_update_rate(1) | sync_pressed(1),
#   [4..18] val[3] : three 5-byte blocks, each eight 5-bit fields
#            (time_0,value_0,time_1,value_1,time_2,value_2,time_3,value_3)
PACKAGE_LEN = 19

# Propane/butane mix, 1.0 = 100% propane (ESPHome default).
PROPANE_BUTANE_MIX = 1.0


def _speed_of_sound(temp_c: float, mix: float = PROPANE_BUTANE_MIX) -> float:
    """LPG speed of sound (m/s) given temperature (C) and propane/butane mix."""
    return (
        1040.71
        - 4.87 * temp_c
        - 137.5 * mix
        - 0.0107 * temp_c * temp_c
        - 1.63 * temp_c * mix
    )


class MopekaStdBluetoothDeviceData(BluetoothData):
    """Data decoder for Mopeka Standard Check BLE sensors."""

    def __init__(self, empty_mm: float = 38.0, full_mm: float = 254.0) -> None:
        """Init with the tank's empty/full liquid-column heights (mm)."""
        super().__init__()
        self._empty_mm = empty_mm
        self._full_mm = full_mm

    def _start_update(self, service_info: BluetoothServiceInfo) -> None:
        """Update from a BLE advertisement."""
        if STD_SERVICE_UUID not in service_info.service_uuids:
            return
        manufacturer_data = service_info.manufacturer_data
        if not manufacturer_data:
            return

        # The Standard sensor emits one manufacturer-data payload; the code does
        # not check the company id, only the length + hardware id byte.
        data: bytes | None = None
        for payload in manufacturer_data.values():
            if len(payload) >= PACKAGE_LEN and (payload[1] & 0xCF) in SENSOR_TYPES:
                data = payload
                break
        if data is None:
            return

        address = service_info.address
        model = SENSOR_TYPES[data[1] & 0xCF]
        self.set_device_manufacturer("Mopeka IOT")
        self.set_device_type(f"{model} Check")
        name = f"{model} Check {short_address(address)}"
        self.set_device_name(name)
        self.set_title(name)

        raw_voltage = data[2]
        raw_temp = data[3] & 0x3F

        # Temperature (C)
        temp_c = -40.0 if raw_temp == 0 else (raw_temp - 25.0) * 1.776964

        # Battery: raw -> volts -> % (CR2032 curve)
        voltage = (raw_voltage / 256.0) * 2.0 + 1.5
        battery_pct = max(0.0, min(100.0, (voltage - 2.2) / 0.65 * 100.0))

        # Unpack the 12 (time, amplitude) measurement pairs. Each 5-byte block is
        # a little-endian 40-bit value with 5-bit fields, LSB first.
        times: list[int] = []
        values: list[int] = []
        for blk in range(3):
            off = 4 + blk * 5
            raw = int.from_bytes(data[off : off + 5], "little")
            for m in range(4):
                times.append(((raw >> (10 * m)) & 0x1F) + 1)
                values.append((raw >> (10 * m + 5)) & 0x1F)

        # Peak detection: strongest echo amplitude and its accumulated time.
        number_usable = 0
        best_value = 0
        best_time = 0
        measurement_time = 0
        for i in range(12):
            measurement_time += times[i]
            if values[i] != 0:
                number_usable += 1
                if values[i] > best_value:
                    best_value = values[i]
                    best_time = measurement_time
                measurement_time = 0

        # Distance (mm) of the liquid column above the bottom-mounted sensor.
        distance_mm = round(_speed_of_sound(temp_c) * best_time / 100.0)
        valid = number_usable >= 1 and best_value >= 2 and best_time >= 2

        # Tank fill percentage from the selected tank preset (linear empty->full).
        # The sensor is broadcasting (we are decoding an advert), so if it returns
        # no usable echo the tank has no liquid surface to reflect off -> it's
        # empty. Report 0% in that case rather than unknown. (An out-of-range or
        # dead sensor stops broadcasting entirely and HA marks it unavailable.)
        tank_percent: int | None = None
        if self._full_mm > self._empty_mm:
            if valid:
                pct = (
                    (distance_mm - self._empty_mm)
                    / (self._full_mm - self._empty_mm)
                    * 100.0
                )
                tank_percent = int(round(max(0.0, min(100.0, pct))))
            else:
                tank_percent = 0

        self.update_predefined_sensor(
            SensorLibrary.TEMPERATURE__CELSIUS, round(temp_c, 1)
        )
        self.update_predefined_sensor(
            SensorLibrary.BATTERY__PERCENTAGE, int(battery_pct)
        )
        self.update_predefined_sensor(
            SensorLibrary.VOLTAGE__ELECTRIC_POTENTIAL_VOLT,
            round(voltage, 3),
            name="Battery Voltage",
            key="battery_voltage",
        )
        self.update_sensor(
            "tank_level",
            Units.LENGTH_MILLIMETERS,
            distance_mm if valid else None,
            SensorDeviceClass.DISTANCE,
            "Tank Level",
        )
        self.update_sensor(
            "tank_level_percent",
            Units.PERCENTAGE,
            tank_percent,
            None,
            "Tank Level Percent",
        )
        self.update_sensor(
            "reading_quality",
            None,
            best_value,
            None,
            "Reading Quality",
        )
