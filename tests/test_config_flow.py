import pytest
from unittest.mock import MagicMock, patch
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak

from custom_components.govee_h6006.const import DOMAIN


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
