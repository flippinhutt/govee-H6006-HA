import sys
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

# Stub out bleak and bleak_retry_connector so api.py can be imported without
# the packages installed. The fixtures below provide the actual mock objects
# that tests interact with.
_bleak_stub = MagicMock()
_bleak_stub.BleakClient = MagicMock
_bleak_stub.BLEDevice = MagicMock
sys.modules.setdefault("bleak", _bleak_stub)
sys.modules.setdefault("bleak.backends", MagicMock())
sys.modules.setdefault("bleak.backends.characteristic", MagicMock())
_bleak_retry_stub = MagicMock()
_bleak_retry_stub.establish_connection = AsyncMock()
sys.modules.setdefault("bleak_retry_connector", _bleak_retry_stub)

# Stub out homeassistant so coordinator.py can be imported without the package
# installed. DataUpdateCoordinator is given a minimal concrete base that stores
# hass, logger, name, and update_interval and exposes async_set_updated_data.
class _DataUpdateCoordinator:
    def __init__(self, hass, logger, *, name, update_interval):
        self.hass = hass
        self.logger = logger
        self.name = name
        self.update_interval = update_interval
        self.data = None

    def __class_getitem__(cls, item):
        return cls

    def async_set_updated_data(self, data):
        self.data = data

_ha_core_stub = MagicMock()
_ha_core_stub.HomeAssistant = MagicMock

_ha_config_entries_stub = MagicMock()
_ha_config_entries_stub.ConfigEntry = MagicMock

_ha_bluetooth_stub = MagicMock()
_ha_bluetooth_stub.async_ble_device_from_address = MagicMock(return_value=None)

_ha_update_coordinator_stub = MagicMock()
_ha_update_coordinator_stub.DataUpdateCoordinator = _DataUpdateCoordinator
_ha_update_coordinator_stub.UpdateFailed = Exception

_ha_passive_coordinator_stub = MagicMock()
_ha_passive_coordinator_stub.PassiveBluetoothDataUpdateCoordinator = MagicMock

sys.modules.setdefault("homeassistant", MagicMock())
sys.modules.setdefault("homeassistant.core", _ha_core_stub)
sys.modules.setdefault("homeassistant.config_entries", _ha_config_entries_stub)
sys.modules.setdefault("homeassistant.components", MagicMock())
sys.modules.setdefault("homeassistant.components.bluetooth", _ha_bluetooth_stub)
sys.modules.setdefault("homeassistant.components.bluetooth.passive_update_coordinator", _ha_passive_coordinator_stub)
sys.modules.setdefault("homeassistant.helpers", MagicMock())
sys.modules.setdefault("homeassistant.helpers.update_coordinator", _ha_update_coordinator_stub)

@pytest.fixture
def mock_bleak_client():
    with patch("custom_components.govee_h6006.api.BleakClient") as mock:
        client = AsyncMock()
        client.is_connected = True
        mock.return_value = client
        yield client

@pytest.fixture
def mock_ble_device():
    device = MagicMock()
    device.address = "AA:BB:CC:DD:EE:FF"
    device.name = "ihoment_H6006"
    return device
