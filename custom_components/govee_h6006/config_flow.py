from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow

from .const import DISCOVERY_NAME, DOMAIN


class GoveeH6006ConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovered_devices: dict[str, BluetoothServiceInfoBleak] = {}

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> dict:
        self._discovery_info = discovery_info
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        if self._discovery_info is None:
            return self.async_abort(reason="no_devices_found")
        if user_input is not None:
            return self.async_create_entry(
                title=self._discovery_info.name,
                data={
                    "address": self._discovery_info.address,
                    "name": self._discovery_info.name,
                },
            )
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={"name": self._discovery_info.name},
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        if user_input is not None:
            address = user_input["address"]
            self._discovery_info = self._discovered_devices[address]
            # Show confirmation form before creating the entry
            return await self.async_step_bluetooth_confirm()

        current_addresses = self._async_current_ids()
        # connectable=True — H6006 requires an active GATT connection, not passive advertising
        for info in async_discovered_service_info(self.hass, connectable=True):
            if info.address in current_addresses or info.address in self._discovered_devices:
                continue
            if not info.name.startswith(DISCOVERY_NAME):
                continue
            self._discovered_devices[info.address] = info

        if not self._discovered_devices:
            return self.async_abort(reason="no_devices_found")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required("address"): vol.In(
                    {addr: info.name for addr, info in self._discovered_devices.items()}
                )}
            ),
        )
