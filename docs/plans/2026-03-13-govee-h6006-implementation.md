# Govee H6006 BLE Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a local-only HACS Home Assistant integration for the Govee H6006 bulb over Bluetooth.

**Architecture:** Custom HA component with a config flow for BLE discovery, a DataUpdateCoordinator that manages a persistent GATT connection, and a LightEntity exposing power, brightness, RGB, and color temperature. All communication is local — no cloud.

**Tech Stack:** Python 3.11+, `bleak`, `bleak-retry-connector`, `pytest`, `pytest-homeassistant-custom-component`

---

## Setup

Before starting, install test dependencies (ask user to approve):

```bash
pip install pytest pytest-asyncio pytest-homeassistant-custom-component
```

All tests live in `tests/`. Run the full suite with:
```bash
pytest tests/ -v
```

---

### Task 1: Project Scaffold

**Files:**
- Create: `custom_components/govee_h6006/__init__.py`
- Create: `custom_components/govee_h6006/manifest.json`
- Create: `custom_components/govee_h6006/const.py`
- Create: `hacs.json`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

**Step 1: Create the directory structure**

```bash
mkdir -p custom_components/govee_h6006/translations tests
touch custom_components/govee_h6006/__init__.py tests/__init__.py
```

**Step 2: Write `manifest.json`**

```json
{
  "domain": "govee_h6006",
  "name": "Govee H6006 BLE",
  "bluetooth": [
    { "local_name": "ihoment_*", "connectable": true }
  ],
  "codeowners": [],
  "config_flow": true,
  "dependencies": ["bluetooth"],
  "documentation": "",
  "iot_class": "local_polling",
  "requirements": ["bleak-retry-connector>=3.0.0"],
  "version": "1.0.0"
}
```

**Step 3: Write `const.py`**

```python
DOMAIN = "govee_h6006"
DISCOVERY_NAME = "ihoment_"

SERVICE_UUID = "00010203-0405-0607-0809-0a0b0c0d1910"
WRITE_CHARACTERISTIC_UUID = "00010203-0405-0607-0809-0a0b0c0d2b11"
READ_CHARACTERISTIC_UUID = "00010203-0405-0607-0809-0a0b0c0d2b10"

MIN_KELVIN = 2700
MAX_KELVIN = 6500
```

**Step 4: Write `hacs.json`**

```json
{
  "name": "Govee H6006 BLE",
  "render_readme": true
}
```

**Step 5: Write `tests/conftest.py`**

```python
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
```

**Step 6: Commit**

```bash
git add custom_components/ tests/ hacs.json
git commit -m "chore: scaffold govee_h6006 integration structure"
```

---

### Task 2: Packet Protocol

**Files:**
- Create: `custom_components/govee_h6006/api_utils.py`
- Create: `tests/test_api_utils.py`

**Step 1: Write the failing tests**

```python
# tests/test_api_utils.py
import pytest
from custom_components.govee_h6006.api_utils import GoveePacket


def test_power_on_packet():
    frame = GoveePacket.power(True)
    assert len(frame) == 20
    assert frame[0] == 0x33       # COMMAND head
    assert frame[1] == 0x01       # POWER cmd
    assert frame[2] == 0x01       # ON
    assert _valid_checksum(frame)


def test_power_off_packet():
    frame = GoveePacket.power(False)
    assert frame[2] == 0x00
    assert _valid_checksum(frame)


def test_brightness_packet():
    frame = GoveePacket.brightness(128)
    assert frame[0] == 0x33
    assert frame[1] == 0x04
    assert frame[2] == 128
    assert _valid_checksum(frame)


def test_brightness_clamps_to_range():
    assert GoveePacket.brightness(0)[2] == 0
    assert GoveePacket.brightness(255)[2] == 255


def test_rgb_packet():
    frame = GoveePacket.color_rgb(255, 0, 128)
    assert frame[0] == 0x33
    assert frame[1] == 0x05
    assert frame[2] == 0x02       # color mode
    assert frame[3] == 255        # R
    assert frame[4] == 0          # G
    assert frame[5] == 128        # B
    assert _valid_checksum(frame)


def test_color_temp_packet_warm():
    frame = GoveePacket.color_temp(2700)
    assert frame[0] == 0x33
    assert frame[1] == 0x05
    assert frame[2] == 0x02       # color mode
    assert frame[3] == 0xFF       # white R
    assert frame[4] == 0xFF       # white G
    assert frame[5] == 0xFF       # white B
    assert frame[6] == 0x01       # white sub-mode
    assert frame[7] == 255        # warm = max at 2700K
    assert frame[8] == 0          # cold = 0 at 2700K
    assert _valid_checksum(frame)


def test_color_temp_packet_cold():
    frame = GoveePacket.color_temp(6500)
    assert frame[7] == 0          # warm = 0 at 6500K
    assert frame[8] == 255        # cold = max at 6500K
    assert _valid_checksum(frame)


def test_checksum_is_xor_of_first_19_bytes():
    frame = GoveePacket.power(True)
    expected = 0
    for b in frame[:19]:
        expected ^= b
    assert frame[19] == expected


def _valid_checksum(frame: bytes) -> bool:
    xor = 0
    for b in frame[:19]:
        xor ^= b
    return frame[19] == xor
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_api_utils.py -v
```
Expected: `ModuleNotFoundError` or `ImportError` — `api_utils` doesn't exist yet.

**Step 3: Write `api_utils.py`**

```python
from __future__ import annotations
from .const import MIN_KELVIN, MAX_KELVIN

_PACKET_LEN = 20
_CMD_HEAD = 0x33


def _build_frame(cmd: int, payload: list[int]) -> bytes:
    frame = [_CMD_HEAD, cmd & 0xFF] + payload
    frame += [0] * (_PACKET_LEN - 1 - len(frame))
    checksum = 0
    for b in frame:
        checksum ^= b
    frame.append(checksum & 0xFF)
    return bytes(frame)


class GoveePacket:
    @staticmethod
    def power(on: bool) -> bytes:
        return _build_frame(0x01, [0x01 if on else 0x00])

    @staticmethod
    def brightness(value: int) -> bytes:
        value = max(0, min(255, value))
        return _build_frame(0x04, [value])

    @staticmethod
    def color_rgb(r: int, g: int, b: int) -> bytes:
        return _build_frame(0x05, [0x02, r, g, b])

    @staticmethod
    def color_temp(kelvin: int) -> bytes:
        kelvin = max(MIN_KELVIN, min(MAX_KELVIN, kelvin))
        warm = round((MAX_KELVIN - kelvin) / (MAX_KELVIN - MIN_KELVIN) * 255)
        cold = 255 - warm
        return _build_frame(0x05, [0x02, 0xFF, 0xFF, 0xFF, 0x01, warm, cold])
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_api_utils.py -v
```
Expected: All 8 tests PASS.

**Step 5: Commit**

```bash
git add custom_components/govee_h6006/api_utils.py tests/test_api_utils.py
git commit -m "feat: add BLE packet protocol with full test coverage"
```

---

### Task 3: BLE API

**Files:**
- Create: `custom_components/govee_h6006/api.py`
- Create: `tests/test_api.py`

**Step 1: Write the failing tests**

```python
# tests/test_api.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from custom_components.govee_h6006.api import GoveeAPI
from custom_components.govee_h6006.api_utils import GoveePacket


@pytest.fixture
def update_callback():
    return AsyncMock()


@pytest.fixture
def api(mock_ble_device, update_callback):
    return GoveeAPI(mock_ble_device, update_callback)


@pytest.mark.asyncio
async def test_send_connects_before_transmitting(api, mock_bleak_client):
    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client) as mock_connect:
        await api.set_power(True)
        mock_connect.assert_called_once()
        mock_bleak_client.write_gatt_char.assert_called_once()


@pytest.mark.asyncio
async def test_send_reuses_existing_connection(api, mock_bleak_client):
    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client) as mock_connect:
        await api.set_power(True)
        await api.set_power(False)
        # establish_connection called only once — reuses connection
        assert mock_connect.call_count == 1
        assert mock_bleak_client.write_gatt_char.call_count == 2


@pytest.mark.asyncio
async def test_set_power_sends_correct_packet(api, mock_bleak_client):
    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client):
        await api.set_power(True)
        args = mock_bleak_client.write_gatt_char.call_args
        packet = args[0][1]
        assert packet[0] == 0x33
        assert packet[1] == 0x01
        assert packet[2] == 0x01


@pytest.mark.asyncio
async def test_set_brightness_sends_correct_packet(api, mock_bleak_client):
    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client):
        await api.set_brightness(200)
        args = mock_bleak_client.write_gatt_char.call_args
        packet = args[0][1]
        assert packet[1] == 0x04
        assert packet[2] == 200


@pytest.mark.asyncio
async def test_set_rgb_sends_correct_packet(api, mock_bleak_client):
    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client):
        await api.set_color_rgb(255, 100, 50)
        args = mock_bleak_client.write_gatt_char.call_args
        packet = args[0][1]
        assert packet[1] == 0x05
        assert packet[3] == 255
        assert packet[4] == 100
        assert packet[5] == 50


@pytest.mark.asyncio
async def test_set_color_temp_sends_correct_packet(api, mock_bleak_client):
    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client):
        await api.set_color_temp(2700)
        args = mock_bleak_client.write_gatt_char.call_args
        packet = args[0][1]
        assert packet[1] == 0x05
        assert packet[6] == 0x01   # white sub-mode
        assert packet[7] == 255    # warm max at 2700K


@pytest.mark.asyncio
async def test_notification_updates_state(api, mock_bleak_client, update_callback):
    with patch("custom_components.govee_h6006.api.establish_connection",
               return_value=mock_bleak_client):
        await api.set_power(True)

    # Simulate a power-state notification from device
    power_on_response = bytearray(GoveePacket.power(True))
    power_on_response[0] = 0xAA  # REQUEST head = device response
    # Recalculate checksum
    xor = 0
    for b in power_on_response[:19]:
        xor ^= b
    power_on_response[19] = xor

    await api._handle_notification(None, power_on_response)
    assert api.state is True
    update_callback.assert_called_once()
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_api.py -v
```
Expected: `ImportError` — `api.py` doesn't exist yet.

**Step 3: Write `api.py`**

```python
from __future__ import annotations
import logging
from bleak import BleakClient, BLEDevice
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak_retry_connector import establish_connection

from .const import WRITE_CHARACTERISTIC_UUID, READ_CHARACTERISTIC_UUID
from .api_utils import GoveePacket, _build_frame

_LOGGER = logging.getLogger(__name__)

_REQUEST_HEAD = 0xAA
_POWER_CMD = 0x01
_BRIGHTNESS_CMD = 0x04
_COLOR_CMD = 0x05


class GoveeAPI:
    state: bool | None = None
    brightness: int | None = None
    color_rgb: tuple[int, int, int] | None = None
    color_temp: int | None = None

    def __init__(self, ble_device: BLEDevice, update_callback) -> None:
        self._ble_device = ble_device
        self._update_callback = update_callback
        self._client: BleakClient | None = None

    @property
    def address(self) -> str:
        return self._ble_device.address

    async def _ensure_connected(self) -> None:
        if self._client is not None and self._client.is_connected:
            return
        self._client = await establish_connection(
            BleakClient, self._ble_device, self.address
        )
        await self._client.start_notify(READ_CHARACTERISTIC_UUID, self._handle_notification)

    async def _write(self, packet: bytes) -> None:
        await self._ensure_connected()
        await self._client.write_gatt_char(WRITE_CHARACTERISTIC_UUID, packet, False)

    async def _handle_notification(
        self, characteristic: BleakGATTCharacteristic | None, frame: bytearray
    ) -> None:
        if len(frame) < 20:
            return
        # Verify checksum
        xor = 0
        for b in frame[:19]:
            xor ^= b
        if (xor & 0xFF) != frame[19]:
            _LOGGER.warning("Received packet with bad checksum, discarding")
            return
        if frame[0] != _REQUEST_HEAD:
            return
        cmd = frame[1]
        if cmd == _POWER_CMD:
            self.state = frame[2] == 0x01
        elif cmd == _BRIGHTNESS_CMD:
            self.brightness = frame[2]
        elif cmd == _COLOR_CMD:
            if frame[6] == 0x01:  # white mode
                # Reconstruct approximate kelvin from warm byte
                from .const import MIN_KELVIN, MAX_KELVIN
                warm = frame[7]
                self.color_temp = round(MAX_KELVIN - (warm / 255) * (MAX_KELVIN - MIN_KELVIN))
            else:
                self.color_rgb = (frame[3], frame[4], frame[5])
        await self._update_callback()

    async def set_power(self, on: bool) -> None:
        await self._write(GoveePacket.power(on))

    async def set_brightness(self, value: int) -> None:
        await self._write(GoveePacket.brightness(value))

    async def set_color_rgb(self, r: int, g: int, b: int) -> None:
        await self._write(GoveePacket.color_rgb(r, g, b))

    async def set_color_temp(self, kelvin: int) -> None:
        await self._write(GoveePacket.color_temp(kelvin))
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_api.py -v
```
Expected: All 7 tests PASS.

**Step 5: Commit**

```bash
git add custom_components/govee_h6006/api.py tests/test_api.py
git commit -m "feat: add GoveeAPI BLE connection and command layer"
```

---

### Task 4: Coordinator

**Files:**
- Create: `custom_components/govee_h6006/coordinator.py`
- Create: `tests/test_coordinator.py`

**Step 1: Write the failing tests**

```python
# tests/test_coordinator.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant.core import HomeAssistant
from custom_components.govee_h6006.coordinator import GoveeCoordinator


@pytest.fixture
def config_entry():
    entry = MagicMock()
    entry.data = {
        "address": "AA:BB:CC:DD:EE:FF",
        "name": "ihoment_H6006",
    }
    entry.unique_id = "AA:BB:CC:DD:EE:FF"
    return entry


@pytest.fixture
def mock_hass():
    hass = MagicMock(spec=HomeAssistant)
    return hass


@pytest.mark.asyncio
async def test_coordinator_polls_device_state(mock_hass, config_entry, mock_ble_device):
    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        return_value=mock_ble_device,
    ), patch("custom_components.govee_h6006.coordinator.GoveeAPI") as MockAPI:
        api_instance = AsyncMock()
        api_instance.state = True
        api_instance.brightness = 200
        api_instance.color_rgb = (255, 0, 0)
        api_instance.color_temp = None
        MockAPI.return_value = api_instance

        coordinator = GoveeCoordinator(mock_hass, config_entry)
        data = await coordinator._async_update_data()

        assert data.state is True
        assert data.brightness == 200
        assert data.color_rgb == (255, 0, 0)


@pytest.mark.asyncio
async def test_coordinator_raises_when_device_not_found(mock_hass, config_entry):
    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        return_value=None,
    ):
        with pytest.raises(Exception):
            GoveeCoordinator(mock_hass, config_entry)


@pytest.mark.asyncio
async def test_coordinator_set_power_delegates_to_api(mock_hass, config_entry, mock_ble_device):
    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        return_value=mock_ble_device,
    ), patch("custom_components.govee_h6006.coordinator.GoveeAPI") as MockAPI:
        api_instance = AsyncMock()
        MockAPI.return_value = api_instance

        coordinator = GoveeCoordinator(mock_hass, config_entry)
        await coordinator.set_power(True)
        api_instance.set_power.assert_called_once_with(True)
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_coordinator.py -v
```
Expected: `ImportError` — `coordinator.py` doesn't exist yet.

**Step 3: Write `coordinator.py`**

```python
from __future__ import annotations
from dataclasses import dataclass
from datetime import timedelta
import logging

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.components.bluetooth.passive_update_coordinator import PassiveBluetoothDataUpdateCoordinator

from .api import GoveeAPI
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass
class GoveeData:
    state: bool | None = None
    brightness: int | None = None
    color_rgb: tuple[int, int, int] | None = None
    color_temp: int | None = None


class GoveeCoordinator(DataUpdateCoordinator[GoveeData]):
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        self.device_address = config_entry.data["address"]
        self.device_name = config_entry.data["name"]

        ble_device = bluetooth.async_ble_device_from_address(
            hass, self.device_address, connectable=True
        )
        if ble_device is None:
            raise RuntimeError(f"BLE device {self.device_address} not found")

        self._api = GoveeAPI(ble_device, self._async_push_data)

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} ({self.device_address})",
            update_interval=timedelta(seconds=15),
        )

    def _snapshot(self) -> GoveeData:
        return GoveeData(
            state=self._api.state,
            brightness=self._api.brightness,
            color_rgb=self._api.color_rgb,
            color_temp=self._api.color_temp,
        )

    async def _async_push_data(self) -> None:
        self.async_set_updated_data(self._snapshot())

    async def _async_update_data(self) -> GoveeData:
        return self._snapshot()

    async def set_power(self, on: bool) -> None:
        await self._api.set_power(on)

    async def set_brightness(self, value: int) -> None:
        await self._api.set_brightness(value)

    async def set_color_rgb(self, r: int, g: int, b: int) -> None:
        await self._api.set_color_rgb(r, g, b)

    async def set_color_temp(self, kelvin: int) -> None:
        await self._api.set_color_temp(kelvin)
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_coordinator.py -v
```
Expected: All 3 tests PASS.

**Step 5: Commit**

```bash
git add custom_components/govee_h6006/coordinator.py tests/test_coordinator.py
git commit -m "feat: add coordinator with state management"
```

---

### Task 5: Config Flow

**Files:**
- Create: `custom_components/govee_h6006/config_flow.py`
- Create: `custom_components/govee_h6006/translations/en.json`
- Create: `tests/test_config_flow.py`

**Step 1: Write the failing tests**

```python
# tests/test_config_flow.py
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
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_config_flow.py -v
```
Expected: `ImportError` — `config_flow.py` doesn't exist yet.

**Step 3: Write `config_flow.py`**

```python
from __future__ import annotations
from typing import Any

import voluptuous as vol
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, DISCOVERY_NAME


class GoveeH6006ConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovered_devices: dict[str, BluetoothServiceInfoBleak] = {}

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        self._discovery_info = discovery_info
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        assert self._discovery_info is not None
        if user_input is not None:
            return self.async_create_entry(
                title=self._discovery_info.name,
                data={
                    "address": self._discovery_info.address,
                    "name": self._discovery_info.name,
                },
            )
        return self.async_show_form(step_id="bluetooth_confirm")

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            address = user_input["address"]
            self._discovery_info = self._discovered_devices[address]
            return await self.async_step_bluetooth_confirm()

        current_addresses = self._async_current_ids()
        for info in async_discovered_service_info(self.hass, connectable=True):
            if info.address in current_addresses or info.address in self._discovered_devices:
                continue
            if not info.name.startswith(DISCOVERY_NAME):
                continue
            self._discovered_devices[info.address] = info

        if not self._discovered_devices:
            return self.async_abort(reason="no_devices_found")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required("address"): vol.In(
                    {addr: info.name for addr, info in self._discovered_devices.items()}
                )}
            ),
        )
```

**Step 4: Write `translations/en.json`**

```json
{
  "config": {
    "step": {
      "bluetooth_confirm": {
        "title": "Set up Govee H6006",
        "description": "Add {name} to Home Assistant?"
      },
      "user": {
        "title": "Set up Govee H6006",
        "data": {
          "address": "Device"
        }
      }
    },
    "abort": {
      "no_devices_found": "No Govee H6006 devices found nearby.",
      "already_configured": "Device is already configured."
    }
  }
}
```

**Step 5: Run tests to verify they pass**

```bash
pytest tests/test_config_flow.py -v
```
Expected: All 4 tests PASS.

**Step 6: Commit**

```bash
git add custom_components/govee_h6006/config_flow.py \
        custom_components/govee_h6006/translations/ \
        tests/test_config_flow.py
git commit -m "feat: add config flow with bluetooth auto-discovery"
```

---

### Task 6: Light Entity

**Files:**
- Create: `custom_components/govee_h6006/light.py`
- Create: `tests/test_light.py`

**Step 1: Write the failing tests**

```python
# tests/test_light.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from homeassistant.components.light import ColorMode
from custom_components.govee_h6006.light import GoveeLight
from custom_components.govee_h6006.coordinator import GoveeData


def make_coordinator(state=True, brightness=255, color_rgb=None, color_temp=None):
    coordinator = MagicMock()
    coordinator.data = GoveeData(
        state=state,
        brightness=brightness,
        color_rgb=color_rgb,
        color_temp=color_temp,
    )
    coordinator.set_power = AsyncMock()
    coordinator.set_brightness = AsyncMock()
    coordinator.set_color_rgb = AsyncMock()
    coordinator.set_color_temp = AsyncMock()
    coordinator.device_name = "ihoment_H6006"
    coordinator.device_address = "AA:BB:CC:DD:EE:FF"
    return coordinator


def make_light(coordinator):
    config_entry = MagicMock()
    config_entry.unique_id = "AA:BB:CC:DD:EE:FF"
    light = GoveeLight(coordinator, config_entry)
    return light


def test_light_is_on_when_state_true():
    light = make_light(make_coordinator(state=True))
    assert light.is_on is True


def test_light_is_off_when_state_false():
    light = make_light(make_coordinator(state=False))
    assert light.is_on is False


def test_brightness_exposed_correctly():
    light = make_light(make_coordinator(brightness=128))
    assert light.brightness == 128


def test_color_mode_rgb_when_color_set():
    light = make_light(make_coordinator(color_rgb=(255, 0, 0), color_temp=None))
    assert light.color_mode == ColorMode.RGB


def test_color_mode_color_temp_when_temp_set():
    light = make_light(make_coordinator(color_rgb=None, color_temp=3000))
    assert light.color_mode == ColorMode.COLOR_TEMP


def test_supported_color_modes():
    light = make_light(make_coordinator())
    assert ColorMode.RGB in light.supported_color_modes
    assert ColorMode.COLOR_TEMP in light.supported_color_modes


def test_color_temp_kelvin_range():
    light = make_light(make_coordinator())
    assert light.min_color_temp_kelvin == 2700
    assert light.max_color_temp_kelvin == 6500


@pytest.mark.asyncio
async def test_turn_on_calls_set_power():
    coordinator = make_coordinator(state=False)
    light = make_light(coordinator)
    await light.async_turn_on()
    coordinator.set_power.assert_called_once_with(True)


@pytest.mark.asyncio
async def test_turn_on_with_brightness():
    coordinator = make_coordinator()
    light = make_light(coordinator)
    await light.async_turn_on(brightness=100)
    coordinator.set_brightness.assert_called_once_with(100)


@pytest.mark.asyncio
async def test_turn_on_with_rgb():
    coordinator = make_coordinator()
    light = make_light(coordinator)
    await light.async_turn_on(rgb_color=(255, 128, 0))
    coordinator.set_color_rgb.assert_called_once_with(255, 128, 0)


@pytest.mark.asyncio
async def test_turn_on_with_color_temp():
    coordinator = make_coordinator()
    light = make_light(coordinator)
    await light.async_turn_on(color_temp_kelvin=4000)
    coordinator.set_color_temp.assert_called_once_with(4000)


@pytest.mark.asyncio
async def test_turn_off():
    coordinator = make_coordinator(state=True)
    light = make_light(coordinator)
    await light.async_turn_off()
    coordinator.set_power.assert_called_once_with(False)
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_light.py -v
```
Expected: `ImportError` — `light.py` doesn't exist yet.

**Step 3: Write `light.py`**

```python
from __future__ import annotations
from typing import Any

from homeassistant.components.light import (
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MIN_KELVIN, MAX_KELVIN
from .coordinator import GoveeCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: GoveeCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([GoveeLight(coordinator, config_entry)])


class GoveeLight(CoordinatorEntity[GoveeCoordinator], LightEntity):
    _attr_supported_color_modes = {ColorMode.RGB, ColorMode.COLOR_TEMP}
    _attr_min_color_temp_kelvin = MIN_KELVIN
    _attr_max_color_temp_kelvin = MAX_KELVIN

    def __init__(self, coordinator: GoveeCoordinator, config_entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = config_entry.unique_id
        self._attr_name = coordinator.device_name

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data.state

    @property
    def brightness(self) -> int | None:
        return self.coordinator.data.brightness

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        return self.coordinator.data.color_rgb

    @property
    def color_temp_kelvin(self) -> int | None:
        return self.coordinator.data.color_temp

    @property
    def color_mode(self) -> ColorMode:
        if self.coordinator.data.color_temp is not None:
            return ColorMode.COLOR_TEMP
        return ColorMode.RGB

    async def async_turn_on(self, **kwargs: Any) -> None:
        if not self.is_on:
            await self.coordinator.set_power(True)
        if "brightness" in kwargs:
            await self.coordinator.set_brightness(kwargs["brightness"])
        if "rgb_color" in kwargs:
            r, g, b = kwargs["rgb_color"]
            await self.coordinator.set_color_rgb(r, g, b)
        if "color_temp_kelvin" in kwargs:
            await self.coordinator.set_color_temp(kwargs["color_temp_kelvin"])

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.set_power(False)
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_light.py -v
```
Expected: All 11 tests PASS.

**Step 5: Commit**

```bash
git add custom_components/govee_h6006/light.py tests/test_light.py
git commit -m "feat: add LightEntity with RGB and color temperature support"
```

---

### Task 7: Integration Init

**Files:**
- Modify: `custom_components/govee_h6006/__init__.py`
- Create: `tests/test_init.py`

**Step 1: Write the failing tests**

```python
# tests/test_init.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntryState

from custom_components.govee_h6006.const import DOMAIN


@pytest.mark.asyncio
async def test_setup_entry_stores_coordinator(hass):
    config_entry = MagicMock()
    config_entry.data = {"address": "AA:BB:CC:DD:EE:FF", "name": "ihoment_H6006"}
    config_entry.unique_id = "AA:BB:CC:DD:EE:FF"
    config_entry.entry_id = "test_entry"

    mock_ble_device = MagicMock()
    mock_ble_device.address = "AA:BB:CC:DD:EE:FF"

    with patch(
        "custom_components.govee_h6006.coordinator.bluetooth.async_ble_device_from_address",
        return_value=mock_ble_device,
    ), patch(
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
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_init.py -v
```
Expected: FAIL — `__init__.py` is empty.

**Step 3: Write `__init__.py`**

```python
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import GoveeCoordinator

PLATFORMS = [Platform.LIGHT]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = GoveeCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_init.py -v
```
Expected: All 2 tests PASS.

**Step 5: Run the full test suite**

```bash
pytest tests/ -v
```
Expected: All tests PASS.

**Step 6: Commit**

```bash
git add custom_components/govee_h6006/__init__.py tests/test_init.py
git commit -m "feat: add integration setup and teardown"
```

---

## Final Verification

```bash
pytest tests/ -v --tb=short
```

All tests should pass. The integration is ready to install in HA via HACS or by copying `custom_components/govee_h6006/` to your HA config directory.
