"""Config flow for the Mopeka Standard Check integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import callback

from .const import CONF_TANK_TYPE, DEFAULT_TANK_TYPE, DOMAIN, TANK_TYPE_LABELS
from .parser import MopekaStdBluetoothDeviceData as DeviceData


def _tank_selector(default: str = DEFAULT_TANK_TYPE) -> dict:
    """Return a schema fragment for choosing the tank size."""
    return {vol.Required(CONF_TANK_TYPE, default=default): vol.In(TANK_TYPE_LABELS)}


class MopekaStdConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Mopeka Standard Check."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovered_device: DeviceData | None = None
        self._discovered_devices: dict[str, str] = {}

    @callback
    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> MopekaStdOptionsFlow:
        """Return the options flow."""
        return MopekaStdOptionsFlow()

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle the bluetooth discovery step."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        device = DeviceData()
        if not device.supported(discovery_info):
            return self.async_abort(reason="not_supported")
        self._discovery_info = discovery_info
        self._discovered_device = device
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm discovery and choose the tank size."""
        assert self._discovered_device is not None
        assert self._discovery_info is not None
        device = self._discovered_device
        discovery_info = self._discovery_info
        title = device.title or device.get_device_name() or discovery_info.name
        if user_input is not None:
            return self.async_create_entry(
                title=title, data={CONF_TANK_TYPE: user_input[CONF_TANK_TYPE]}
            )

        placeholders = {"name": title}
        self.context["title_placeholders"] = placeholders
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders=placeholders,
            data_schema=vol.Schema(_tank_selector()),
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the user step to pick a discovered device and tank size."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=self._discovered_devices[address],
                data={CONF_TANK_TYPE: user_input[CONF_TANK_TYPE]},
            )

        current_addresses = self._async_current_ids(include_ignore=False)
        for discovery_info in async_discovered_service_info(self.hass, False):
            address = discovery_info.address
            if address in current_addresses or address in self._discovered_devices:
                continue
            device = DeviceData()
            if device.supported(discovery_info):
                self._discovered_devices[address] = (
                    device.title
                    or device.get_device_name()
                    or discovery_info.name
                )

        if not self._discovered_devices:
            return self.async_abort(reason="no_devices_found")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): vol.In(self._discovered_devices),
                    **_tank_selector(),
                }
            ),
        )


class MopekaStdOptionsFlow(config_entries.OptionsFlow):
    """Handle changing the tank size after setup."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the tank size option."""
        if user_input is not None:
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={**self.config_entry.data, CONF_TANK_TYPE: user_input[CONF_TANK_TYPE]},
            )
            return self.async_create_entry(title="", data={})

        current = self.config_entry.data.get(CONF_TANK_TYPE, DEFAULT_TANK_TYPE)
        return self.async_show_form(
            step_id="init", data_schema=vol.Schema(_tank_selector(current))
        )
