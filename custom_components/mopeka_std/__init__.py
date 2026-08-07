"""The Mopeka Standard Check integration."""

from __future__ import annotations

import logging

from homeassistant.components.bluetooth import BluetoothScanningMode
from homeassistant.components.bluetooth.passive_update_processor import (
    PassiveBluetoothProcessorCoordinator,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_TANK_TYPE, DEFAULT_TANK_TYPE, TANK_TYPES
from .parser import MopekaStdBluetoothDeviceData

PLATFORMS: list[Platform] = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)

type MopekaStdConfigEntry = ConfigEntry[PassiveBluetoothProcessorCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: MopekaStdConfigEntry) -> bool:
    """Set up Mopeka Standard Check BLE device from a config entry."""
    address = entry.unique_id
    assert address is not None

    tank_type = entry.data.get(CONF_TANK_TYPE, DEFAULT_TANK_TYPE)
    empty_mm, full_mm = TANK_TYPES.get(tank_type, TANK_TYPES[DEFAULT_TANK_TYPE])
    data = MopekaStdBluetoothDeviceData(empty_mm, full_mm)
    coordinator = entry.runtime_data = PassiveBluetoothProcessorCoordinator(
        hass,
        _LOGGER,
        address=address,
        mode=BluetoothScanningMode.PASSIVE,
        update_method=data.update,
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # only start after all platforms have had a chance to subscribe
    entry.async_on_unload(coordinator.async_start())
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(
    hass: HomeAssistant, entry: MopekaStdConfigEntry
) -> None:
    """Reload the entry when the tank type option changes."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(
    hass: HomeAssistant, entry: MopekaStdConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
