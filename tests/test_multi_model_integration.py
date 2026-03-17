"""Integration tests for multi-model support."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from homeassistant.config_entries import ConfigEntry

from custom_components.govee_h6006.coordinator import GoveeCoordinator
from custom_components.govee_h6006.const import DOMAIN


@pytest.fixture
def mock_ble_device():
    """Mock BLE device."""
    device = Mock()
    device.address = "AA:BB:CC:DD:EE:FF"
    device.name = "ihoment_H6006_1234"
    return device


@pytest.fixture
def mock_hass(mock_ble_device):
    """Mock Home Assistant instance."""
    hass = Mock()
    hass.data = {}

    with patch("custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address", return_value=mock_ble_device):
        yield hass


def make_config_entry(model: str, name: str) -> ConfigEntry:
    """Create a mock config entry."""
    return ConfigEntry(
        version=1,
        domain=DOMAIN,
        title=name,
        data={
            "address": "AA:BB:CC:DD:EE:FF",
            "name": name,
            "model": model,
        },
        options={},
        entry_id="test_entry",
        source="bluetooth",
    )


@pytest.mark.asyncio
async def test_h6006_uses_h6006_protocol(mock_hass):
    """Test that H6006 device uses H6006Protocol."""
    entry = make_config_entry("H6006", "ihoment_H6006_1234")

    with patch("custom_components.govee_h6006.coordinator.GoveeAPI") as mock_api:
        coordinator = GoveeCoordinator(mock_hass, entry)

        # Verify API was instantiated with model_type="H6006"
        mock_api.assert_called_once()
        call_kwargs = mock_api.call_args.kwargs
        assert call_kwargs["model_type"] == "H6006"


@pytest.mark.asyncio
async def test_h6008_uses_h6008_protocol(mock_hass):
    """Test that H6008 device uses H6008Protocol."""
    entry = make_config_entry("H6008", "ihoment_H6008_5678")

    with patch("custom_components.govee_h6006.coordinator.GoveeAPI") as mock_api:
        coordinator = GoveeCoordinator(mock_hass, entry)

        # Verify API was instantiated with model_type="H6008"
        mock_api.assert_called_once()
        call_kwargs = mock_api.call_args.kwargs
        assert call_kwargs["model_type"] == "H6008"


@pytest.mark.asyncio
async def test_h6009_uses_h6009_protocol(mock_hass):
    """Test that H6009 device uses H6009Protocol."""
    entry = make_config_entry("H6009", "ihoment_H6009_9012")

    with patch("custom_components.govee_h6006.coordinator.GoveeAPI") as mock_api:
        coordinator = GoveeCoordinator(mock_hass, entry)

        # Verify API was instantiated with model_type="H6009"
        mock_api.assert_called_once()
        call_kwargs = mock_api.call_args.kwargs
        assert call_kwargs["model_type"] == "H6009"


@pytest.mark.asyncio
async def test_h6003_uses_h6003_protocol(mock_hass):
    """Test that H6003 device uses H6003Protocol."""
    entry = make_config_entry("H6003", "ihoment_H6003_3456")

    with patch("custom_components.govee_h6006.coordinator.GoveeAPI") as mock_api:
        coordinator = GoveeCoordinator(mock_hass, entry)

        # Verify API was instantiated with model_type="H6003"
        mock_api.assert_called_once()
        call_kwargs = mock_api.call_args.kwargs
        assert call_kwargs["model_type"] == "H6003"


@pytest.mark.asyncio
async def test_defaults_to_h6006_when_model_missing(mock_hass):
    """Test backward compatibility: defaults to H6006 if model field missing."""
    entry = ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="ihoment_H6006_1234",
        data={
            "address": "AA:BB:CC:DD:EE:FF",
            "name": "ihoment_H6006_1234",
            # No "model" field (backward compatibility)
        },
        options={},
        entry_id="test_entry",
        source="bluetooth",
    )

    with patch("custom_components.govee_h6006.coordinator.GoveeAPI") as mock_api:
        coordinator = GoveeCoordinator(mock_hass, entry)

        # Should default to H6006
        mock_api.assert_called_once()
        call_kwargs = mock_api.call_args.kwargs
        assert call_kwargs["model_type"] == "H6006"
