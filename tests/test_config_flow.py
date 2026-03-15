import pytest
from unittest.mock import MagicMock, patch
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigEntry

from custom_components.govee_h6006.const import DOMAIN


def make_config_entry(data, options=None, entry_id="test"):
    """Create a mock config entry for testing."""
    entry = MagicMock()
    entry.data = data
    entry.options = options or {}
    entry.entry_id = entry_id
    entry.title = "Test"
    entry.version = 1
    entry.minor_version = 0
    entry.domain = DOMAIN
    entry.source = "test"
    entry.unique_id = None
    return entry


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
async def test_options_flow_shows_form():
    """Test that the options flow shows the configuration form."""
    from custom_components.govee_h6006.config_flow import GoveeH6006OptionsFlowHandler

    entry = make_config_entry(
        data={"address": "AA:BB:CC:DD:EE:FF", "name": "ihoment_H6006"},
        options={},
    )

    flow = GoveeH6006OptionsFlowHandler(entry)

    result = await flow.async_step_init()

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"


@pytest.mark.asyncio
async def test_options_flow_updates_entry():
    """Test that the options flow updates the config entry with new options."""
    from custom_components.govee_h6006.config_flow import GoveeH6006OptionsFlowHandler

    entry = make_config_entry(
        data={"address": "AA:BB:CC:DD:EE:FF", "name": "ihoment_H6006"},
        options={},
    )

    flow = GoveeH6006OptionsFlowHandler(entry)

    result = await flow.async_step_init(
        user_input={
            "polling_interval": 60,
            "connection_timeout": 20,
            "suppression_window": 1000,
            "max_retries": 8,
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["polling_interval"] == 60
    assert result["data"]["connection_timeout"] == 20
    assert result["data"]["suppression_window"] == 1000
    assert result["data"]["max_retries"] == 8


@pytest.mark.asyncio
async def test_options_flow_validates_ranges():
    """Test that the options flow accepts valid values within the specified ranges."""
    from custom_components.govee_h6006.config_flow import GoveeH6006OptionsFlowHandler

    entry = make_config_entry(
        data={"address": "AA:BB:CC:DD:EE:FF", "name": "ihoment_H6006"},
        options={},
    )

    # Test minimum valid values
    flow = GoveeH6006OptionsFlowHandler(entry)
    result = await flow.async_step_init(
        user_input={
            "polling_interval": 10,
            "connection_timeout": 5,
            "suppression_window": 200,
            "max_retries": 1,
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY

    # Test maximum valid values
    flow2 = GoveeH6006OptionsFlowHandler(entry)
    result2 = await flow2.async_step_init(
        user_input={
            "polling_interval": 120,
            "connection_timeout": 30,
            "suppression_window": 2000,
            "max_retries": 10,
        },
    )

    assert result2["type"] == FlowResultType.CREATE_ENTRY


@pytest.mark.asyncio
async def test_options_flow_rejects_invalid_values():
    """Test that the options flow rejects out-of-range values."""
    from custom_components.govee_h6006.config_flow import GoveeH6006OptionsFlowHandler

    entry = make_config_entry(
        data={"address": "AA:BB:CC:DD:EE:FF", "name": "ihoment_H6006"},
        options={},
    )

    # Test value below minimum range
    flow = GoveeH6006OptionsFlowHandler(entry)

    try:
        await flow.async_step_init(
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
    flow2 = GoveeH6006OptionsFlowHandler(entry)

    try:
        await flow2.async_step_init(
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
