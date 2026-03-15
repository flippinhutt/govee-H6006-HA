import pytest
from unittest.mock import MagicMock
from datetime import datetime
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS_MILLIWATT, PERCENTAGE
from homeassistant.helpers.entity import EntityCategory
from custom_components.govee_h6006.sensor import (
    GoveeRSSISensor,
    GoveeConnectionSuccessRateSensor,
    GoveeLastPollSensor,
    GoveeConnectionStateSensor,
    GoveeTotalReconnectionsSensor,
)
from custom_components.govee_h6006.coordinator import GoveeData


def make_coordinator(
    rssi=None,
    connection_success_rate=None,
    last_poll_time=None,
    connection_state="disconnected",
    total_reconnections=0,
):
    coordinator = MagicMock()
    coordinator.data = GoveeData(
        rssi=rssi,
        connection_success_rate=connection_success_rate,
        last_poll_time=last_poll_time,
        connection_state=connection_state,
        total_reconnections=total_reconnections,
    )
    coordinator.device_name = "ihoment_H6006"
    coordinator.device_address = "AA:BB:CC:DD:EE:FF"
    return coordinator


def make_config_entry():
    config_entry = MagicMock()
    config_entry.unique_id = "AA:BB:CC:DD:EE:FF"
    return config_entry


def test_rssi_sensor_native_value():
    coordinator = make_coordinator(rssi=-50)
    sensor = GoveeRSSISensor(coordinator, make_config_entry())
    assert sensor.native_value == -50


def test_rssi_sensor_native_value_none():
    coordinator = make_coordinator(rssi=None)
    sensor = GoveeRSSISensor(coordinator, make_config_entry())
    assert sensor.native_value is None


def test_rssi_sensor_properties():
    coordinator = make_coordinator()
    sensor = GoveeRSSISensor(coordinator, make_config_entry())
    assert sensor._attr_device_class == SensorDeviceClass.SIGNAL_STRENGTH
    assert sensor._attr_native_unit_of_measurement == SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    assert sensor._attr_entity_category == EntityCategory.DIAGNOSTIC
    assert sensor._attr_unique_id == "AA:BB:CC:DD:EE:FF_rssi"
    assert sensor._attr_name == "ihoment_H6006 RSSI"


def test_connection_success_rate_sensor_native_value():
    coordinator = make_coordinator(connection_success_rate=95.5)
    sensor = GoveeConnectionSuccessRateSensor(coordinator, make_config_entry())
    assert sensor.native_value == 95.5


def test_connection_success_rate_sensor_native_value_none():
    coordinator = make_coordinator(connection_success_rate=None)
    sensor = GoveeConnectionSuccessRateSensor(coordinator, make_config_entry())
    assert sensor.native_value is None


def test_connection_success_rate_sensor_properties():
    coordinator = make_coordinator()
    sensor = GoveeConnectionSuccessRateSensor(coordinator, make_config_entry())
    assert sensor._attr_native_unit_of_measurement == PERCENTAGE
    assert sensor._attr_entity_category == EntityCategory.DIAGNOSTIC
    assert sensor._attr_unique_id == "AA:BB:CC:DD:EE:FF_connection_success_rate"
    assert sensor._attr_name == "ihoment_H6006 Connection Success Rate"


def test_last_poll_sensor_native_value():
    test_time = datetime(2026, 3, 15, 12, 0, 0)
    coordinator = make_coordinator(last_poll_time=test_time)
    sensor = GoveeLastPollSensor(coordinator, make_config_entry())
    assert sensor.native_value == test_time


def test_last_poll_sensor_native_value_none():
    coordinator = make_coordinator(last_poll_time=None)
    sensor = GoveeLastPollSensor(coordinator, make_config_entry())
    assert sensor.native_value is None


def test_last_poll_sensor_properties():
    coordinator = make_coordinator()
    sensor = GoveeLastPollSensor(coordinator, make_config_entry())
    assert sensor._attr_device_class == SensorDeviceClass.TIMESTAMP
    assert sensor._attr_entity_category == EntityCategory.DIAGNOSTIC
    assert sensor._attr_unique_id == "AA:BB:CC:DD:EE:FF_last_poll"
    assert sensor._attr_name == "ihoment_H6006 Last Poll"


def test_connection_state_sensor_native_value():
    coordinator = make_coordinator(connection_state="connected")
    sensor = GoveeConnectionStateSensor(coordinator, make_config_entry())
    assert sensor.native_value == "connected"


def test_connection_state_sensor_default_value():
    coordinator = make_coordinator(connection_state="disconnected")
    sensor = GoveeConnectionStateSensor(coordinator, make_config_entry())
    assert sensor.native_value == "disconnected"


def test_connection_state_sensor_properties():
    coordinator = make_coordinator()
    sensor = GoveeConnectionStateSensor(coordinator, make_config_entry())
    assert sensor._attr_entity_category == EntityCategory.DIAGNOSTIC
    assert sensor._attr_unique_id == "AA:BB:CC:DD:EE:FF_connection_state"
    assert sensor._attr_name == "ihoment_H6006 Connection State"


def test_total_reconnections_sensor_native_value():
    coordinator = make_coordinator(total_reconnections=5)
    sensor = GoveeTotalReconnectionsSensor(coordinator, make_config_entry())
    assert sensor.native_value == 5


def test_total_reconnections_sensor_default_value():
    coordinator = make_coordinator(total_reconnections=0)
    sensor = GoveeTotalReconnectionsSensor(coordinator, make_config_entry())
    assert sensor.native_value == 0


def test_total_reconnections_sensor_properties():
    coordinator = make_coordinator()
    sensor = GoveeTotalReconnectionsSensor(coordinator, make_config_entry())
    assert sensor._attr_entity_category == EntityCategory.DIAGNOSTIC
    assert sensor._attr_unique_id == "AA:BB:CC:DD:EE:FF_total_reconnections"
    assert sensor._attr_name == "ihoment_H6006 Total Reconnections"
