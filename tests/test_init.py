import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from custom_components.govee_h6006.const import DOMAIN


@pytest.mark.asyncio
async def test_setup_entry_stores_coordinator(hass):
    config_entry = MagicMock()
    config_entry.data = {"address": "AA:BB:CC:DD:EE:FF", "name": "ihoment_H6006"}
    config_entry.options = {}
    config_entry.unique_id = "AA:BB:CC:DD:EE:FF"
    config_entry.entry_id = "test_entry"

    with patch(
        "custom_components.govee_h6006.__init__.GoveeCoordinator"
    ) as MockCoordinator:
        coordinator = AsyncMock()
        coordinator.async_config_entry_first_refresh = AsyncMock()
        MockCoordinator.return_value = coordinator

        from custom_components.govee_h6006 import async_setup_entry
        result = await async_setup_entry(hass, config_entry)

        assert result is True
        assert DOMAIN in hass.data
        assert config_entry.entry_id in hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_unload_entry_cleans_up(hass):
    config_entry = MagicMock()
    config_entry.entry_id = "test_entry"

    hass.data.setdefault(DOMAIN, {})["test_entry"] = MagicMock()

    with patch.object(hass.config_entries, "async_unload_platforms", return_value=True):
        from custom_components.govee_h6006 import async_unload_entry
        result = await async_unload_entry(hass, config_entry)

        assert result is True
        assert "test_entry" not in hass.data.get(DOMAIN, {})
