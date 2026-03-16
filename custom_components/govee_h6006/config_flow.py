# mypy: ignore-errors
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow, OptionsFlow
from homeassistant.core import callback

from .const import (
    DEFAULT_CONNECTION_TIMEOUT,
    DEFAULT_MAX_RETRIES,
    DEFAULT_POLLING_INTERVAL,
    DEFAULT_SUPPRESSION_WINDOW,
    DISCOVERY_NAME,
    DOMAIN,
    MAX_CONNECTION_TIMEOUT,
    MAX_MAX_RETRIES,
    MAX_POLLING_INTERVAL,
    MAX_SUPPRESSION_WINDOW,
    MIN_CONNECTION_TIMEOUT,
    MIN_MAX_RETRIES,
    MIN_POLLING_INTERVAL,
    MIN_SUPPRESSION_WINDOW,
)


class GoveeH6006ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Govee H6006 BLE."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow."""
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovered_devices: dict[str, BluetoothServiceInfoBleak] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Return the options flow handler."""
        return GoveeH6006OptionsFlowHandler(config_entry)

    @staticmethod
    @callback
    def options_flow(config_entry):
        """Return the options flow handler (alias for async_get_options_flow)."""
        return GoveeH6006OptionsFlowHandler(config_entry)

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> dict:
        """Handle bluetooth discovery.

        Args:
            discovery_info: Discovery information from Bluetooth.
        """
        self._discovery_info = discovery_info
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        """Confirm a device found via bluetooth discovery.

        Args:
            user_input: User input from the confirmation form.
        """
        if self._discovery_info is None:
            return self.async_abort(reason="no_devices_found")
        if user_input is not None:
            return self.async_create_entry(  # type: ignore[no-any-return]
                title=self._discovery_info.name,
                data={
                    "address": self._discovery_info.address,
                    "name": self._discovery_info.name,
                },
            )
        return self.async_show_form(  # type: ignore[no-any-return]
            step_id="bluetooth_confirm",
            description_placeholders={"name": self._discovery_info.name},
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        """Handle a flow initialized by the user via manual addition.

        Args:
            user_input: User input from the device selection form.
        """
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

        return self.async_show_form(  # type: ignore[no-any-return]
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required("address"): vol.In(
                    {addr: info.name for addr, info in self._discovered_devices.items()}
                )}
            ),
        )


class GoveeH6006OptionsFlowHandler(OptionsFlow):  # type: ignore[misc]
    """Handle options flow for Govee H6006."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[Any, Any]:  # type: ignore[type-arg,no-any-return]
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(  # type: ignore[no-any-return]
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "polling_interval",
                        default=self.config_entry.options.get(
                            "polling_interval", DEFAULT_POLLING_INTERVAL
                        ),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_POLLING_INTERVAL, max=MAX_POLLING_INTERVAL),
                    ),
                    vol.Required(
                        "connection_timeout",
                        default=self.config_entry.options.get(
                            "connection_timeout", DEFAULT_CONNECTION_TIMEOUT
                        ),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_CONNECTION_TIMEOUT, max=MAX_CONNECTION_TIMEOUT),
                    ),
                    vol.Required(
                        "suppression_window",
                        default=self.config_entry.options.get(
                            "suppression_window", DEFAULT_SUPPRESSION_WINDOW
                        ),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_SUPPRESSION_WINDOW, max=MAX_SUPPRESSION_WINDOW),
                    ),
                    vol.Required(
                        "max_retries",
                        default=self.config_entry.options.get(
                            "max_retries", DEFAULT_MAX_RETRIES
                        ),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_MAX_RETRIES, max=MAX_MAX_RETRIES),
                    ),
                }
            ),
        )
