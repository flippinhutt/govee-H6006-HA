from unittest.mock import AsyncMock, MagicMock, patch
import pytest

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
