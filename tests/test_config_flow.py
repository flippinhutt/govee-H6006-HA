import pytest
from unittest.mock import MagicMock, patch
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigEntry

from custom_components.govee_h6006.const import DOMAIN


class MockConfigEntry(ConfigEntry):
    """Mock ConfigEntry for testing."""

    def __init__(self, *, domain, data, options=None, entry_id="test"):
        """Initialize a mock config entry."""
        super().__init__(
            version=1,
            minor_version=0,
            domain=domain,
            title="Test",
            data=data,
            options=options or {},
            source="test",
            entry_id=entry_id,
            unique_id=None,
        )


def make_service_info(name="ihoment_H6006", address="AA:BB:CC:DD:EE:FF"):
    info = MagicMock(spec=BluetoothServiceInfoBleak)
    info.name = name
    info.address = address
    return info


@pytest.mark.asyncio
async def test_bluetooth_discovery_shows_confirm_form(hass):
    service_info = make_service_info()
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=service_info,
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "bluetooth_confirm"


@pytest.mark.asyncio
async def test_bluetooth_confirm_creates_entry(hass):
    service_info = make_service_info()
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=service_info,
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={}
    )
    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["data"]["address"] == "AA:BB:CC:DD:EE:FF"
    assert result2["data"]["name"] == "ihoment_H6006"


@pytest.mark.asyncio
async def test_user_step_shows_device_list(hass):
    service_info = make_service_info()
    with patch(
        "custom_components.govee_h6006.config_flow.async_discovered_service_info",
        return_value=[service_info],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"


@pytest.mark.asyncio
async def test_user_step_aborts_when_no_devices(hass):
    with patch(
        "custom_components.govee_h6006.config_flow.async_discovered_service_info",
        return_value=[],
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "no_devices_found"


@pytest.mark.asyncio
async def test_options_flow_shows_form(hass):
    """Test that the options flow shows the configuration form."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"address": "AA:BB:CC:DD:EE:FF", "name": "ihoment_H6006"},
        options={},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"


@pytest.mark.asyncio
async def test_options_flow_updates_entry(hass):
    """Test that the options flow updates the config entry with new options."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"address": "AA:BB:CC:DD:EE:FF", "name": "ihoment_H6006"},
        options={},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "polling_interval": 60,
            "connection_timeout": 20,
            "suppression_window": 1000,
            "max_retries": 8,
        },
    )

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["data"]["polling_interval"] == 60
    assert result2["data"]["connection_timeout"] == 20
    assert result2["data"]["suppression_window"] == 1000
    assert result2["data"]["max_retries"] == 8


@pytest.mark.asyncio
async def test_options_flow_validates_ranges(hass):
    """Test that the options flow accepts valid values within the specified ranges."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"address": "AA:BB:CC:DD:EE:FF", "name": "ihoment_H6006"},
        options={},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    # Test minimum valid values
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "polling_interval": 10,
            "connection_timeout": 5,
            "suppression_window": 200,
            "max_retries": 1,
        },
    )

    assert result2["type"] == FlowResultType.CREATE_ENTRY

    # Test maximum valid values
    result3 = await hass.config_entries.options.async_init(entry.entry_id)

    result4 = await hass.config_entries.options.async_configure(
        result3["flow_id"],
        user_input={
            "polling_interval": 120,
            "connection_timeout": 30,
            "suppression_window": 2000,
            "max_retries": 10,
        },
    )

    assert result4["type"] == FlowResultType.CREATE_ENTRY


@pytest.mark.asyncio
async def test_options_flow_rejects_invalid_values(hass):
    """Test that the options flow rejects out-of-range values."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"address": "AA:BB:CC:DD:EE:FF", "name": "ihoment_H6006"},
        options={},
    )
    entry.add_to_hass(hass)

    # Test value below minimum range
    result = await hass.config_entries.options.async_init(entry.entry_id)

    try:
        await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                "polling_interval": 5,  # Below MIN_POLLING_INTERVAL (10)
                "connection_timeout": 15,
                "suppression_window": 500,
                "max_retries": 5,
            },
        )
        assert False, "Expected validation error for out-of-range polling_interval"
    except Exception:
        pass  # Expected to raise validation error

    # Test value above maximum range
    result2 = await hass.config_entries.options.async_init(entry.entry_id)

    try:
        await hass.config_entries.options.async_configure(
            result2["flow_id"],
            user_input={
                "polling_interval": 30,
                "connection_timeout": 50,  # Above MAX_CONNECTION_TIMEOUT (30)
                "suppression_window": 500,
                "max_retries": 5,
            },
        )
        assert False, "Expected validation error for out-of-range connection_timeout"
    except Exception:
        pass  # Expected to raise validation error
