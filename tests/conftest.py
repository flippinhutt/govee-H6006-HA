import sys
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
