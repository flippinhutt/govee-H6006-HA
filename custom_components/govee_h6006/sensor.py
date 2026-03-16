from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, SIGNAL_STRENGTH_DECIBELS_MILLIWATT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import GoveeCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: GoveeCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([
        GoveeRSSISensor(coordinator, config_entry),
        GoveeConnectionSuccessRateSensor(coordinator, config_entry),
        GoveeLastPollSensor(coordinator, config_entry),
        GoveeConnectionStateSensor(coordinator, config_entry),
        GoveeTotalReconnectionsSensor(coordinator, config_entry),
    ])


class GoveeSensorEntity(CoordinatorEntity[GoveeCoordinator], SensorEntity):  # type: ignore[misc]
    """Base class for Govee sensor entities.

    Provides common device_info for all Govee sensors.
    """

    def __init__(self, coordinator: GoveeCoordinator, config_entry: ConfigEntry) -> None:
        """Initialize Govee sensor entity.

        Args:
            coordinator: The data update coordinator.
            config_entry: The config entry associated with this sensor.
        """
        super().__init__(coordinator)
        self._config_entry = config_entry

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information about this Govee sensor.

        Returns:
            DeviceInfo dictionary with manufacturer, model, and version information.
        """
        return DeviceInfo(
            identifiers={(DOMAIN, self._config_entry.unique_id)},
            name=self.coordinator.device_name,
            manufacturer="Govee",
            model=self.coordinator.data.model_number or "H6006",
            sw_version=self.coordinator.data.firmware_version,
            hw_version=self.coordinator.data.hardware_version,
        )


class GoveeRSSISensor(GoveeSensorEntity):
    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: GoveeCoordinator, config_entry: ConfigEntry) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.unique_id}_rssi"
        self._attr_name = f"{coordinator.device_name} RSSI"

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.rssi  # type: ignore[no-any-return]


class GoveeConnectionSuccessRateSensor(GoveeSensorEntity):
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: GoveeCoordinator, config_entry: ConfigEntry) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.unique_id}_connection_success_rate"
        self._attr_name = f"{coordinator.device_name} Connection Success Rate"

    @property
    def native_value(self) -> float | None:
        return self.coordinator.data.connection_success_rate  # type: ignore[no-any-return]


class GoveeLastPollSensor(GoveeSensorEntity):
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: GoveeCoordinator, config_entry: ConfigEntry) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.unique_id}_last_poll"
        self._attr_name = f"{coordinator.device_name} Last Poll"

    @property
    def native_value(self) -> str | None:  # Added type hint
        return self.coordinator.data.last_poll_time  # type: ignore[no-any-return]


class GoveeConnectionStateSensor(GoveeSensorEntity):
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: GoveeCoordinator, config_entry: ConfigEntry) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.unique_id}_connection_state"
        self._attr_name = f"{coordinator.device_name} Connection State"

    @property
    def native_value(self) -> str:
        return self.coordinator.data.connection_state  # type: ignore[no-any-return]


class GoveeTotalReconnectionsSensor(GoveeSensorEntity):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator: GoveeCoordinator, config_entry: ConfigEntry) -> None:
        super().__init__(coordinator, config_entry)
        self._attr_unique_id = f"{config_entry.unique_id}_total_reconnections"
        self._attr_name = f"{coordinator.device_name} Total Reconnections"

    @property
    async def _async_update_data(self) -> int:
        """Fetch data from API."""
        return await self.coordinator.api.get_total_reconnections()  # type: ignore[no-any-return]

    @property
    def native_value(self) -> int:
        return self.coordinator.data.total_reconnections  # type: ignore[no-any-return]
