import sys
import enum
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

# Stub voluptuous so config_flow.py can be imported without the package
_vol_stub = MagicMock()
_vol_stub.Schema = lambda x: x
_vol_stub.Required = lambda x: x
_vol_stub.In = lambda x: x
sys.modules.setdefault("voluptuous", _vol_stub)

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

    async def async_config_entry_first_refresh(self):
        pass


class _FlowResultType(str, enum.Enum):
    FORM = "form"
    CREATE_ENTRY = "create_entry"
    ABORT = "abort"


_ha_core_stub = MagicMock()
_ha_core_stub.HomeAssistant = MagicMock

_ha_config_entries_stub = MagicMock()
_ha_config_entries_stub.ConfigEntry = MagicMock

class _ConfigFlow:
    """Minimal ConfigFlow base that accepts domain= as a class keyword."""
    def __init_subclass__(cls, domain=None, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._domain = domain

    def async_show_form(self, *, step_id, data_schema=None, description_placeholders=None):
        """Return a form result."""
        return {
            "type": _FlowResultType.FORM,
            "step_id": step_id,
            "data_schema": data_schema,
            "description_placeholders": description_placeholders or {},
        }

    def async_create_entry(self, *, title, data):
        """Create a config entry."""
        return {
            "type": _FlowResultType.CREATE_ENTRY,
            "title": title,
            "data": data,
        }

    def async_abort(self, *, reason):
        """Abort the config flow."""
        return {
            "type": _FlowResultType.ABORT,
            "reason": reason,
        }

_ha_config_entries_stub.ConfigFlow = _ConfigFlow
_ha_config_entries_stub.SOURCE_BLUETOOTH = "bluetooth"
_ha_config_entries_stub.SOURCE_USER = "user"

_ha_data_entry_flow_stub = MagicMock()
_ha_data_entry_flow_stub.FlowResultType = _FlowResultType

_ha_bluetooth_stub = MagicMock()
_ha_bluetooth_stub.async_ble_device_from_address = MagicMock(return_value=None)
_ha_bluetooth_stub.BluetoothServiceInfoBleak = MagicMock
_ha_bluetooth_stub.async_discovered_service_info = MagicMock(return_value=[])

_ha_update_coordinator_stub = MagicMock()
_ha_update_coordinator_stub.DataUpdateCoordinator = _DataUpdateCoordinator
_ha_update_coordinator_stub.UpdateFailed = Exception

_ha_passive_coordinator_stub = MagicMock()
_ha_passive_coordinator_stub.PassiveBluetoothDataUpdateCoordinator = MagicMock

# Stub homeassistant.components.light with ColorMode and LightEntity
class _ColorMode(str, enum.Enum):
    RGB = "rgb"
    COLOR_TEMP = "color_temp"
    ONOFF = "onoff"
    BRIGHTNESS = "brightness"
    UNKNOWN = "unknown"

class _LightEntity:
    pass

_ha_light_stub = MagicMock()
_ha_light_stub.ColorMode = _ColorMode
_ha_light_stub.LightEntity = _LightEntity

# Stub homeassistant.const with Platform
class _Platform(str, enum.Enum):
    LIGHT = "light"

_ha_const_stub = MagicMock()
_ha_const_stub.Platform = _Platform

# Stub homeassistant.exceptions with HomeAssistantError
class _HomeAssistantError(Exception):
    pass

_ha_exceptions_stub = MagicMock()
_ha_exceptions_stub.HomeAssistantError = _HomeAssistantError

# CoordinatorEntity stub that stores coordinator
class _CoordinatorEntity:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

    def __class_getitem__(cls, item):
        return cls

    def __init__(self, coordinator):
        self.coordinator = coordinator

_ha_update_coordinator_stub.CoordinatorEntity = _CoordinatorEntity

# Stub entity_platform
_ha_entity_platform_stub = MagicMock()

sys.modules["homeassistant"] = MagicMock()
sys.modules["homeassistant.core"] = _ha_core_stub
sys.modules["homeassistant.config_entries"] = _ha_config_entries_stub
sys.modules["homeassistant.data_entry_flow"] = _ha_data_entry_flow_stub
sys.modules["homeassistant.const"] = _ha_const_stub
sys.modules["homeassistant.exceptions"] = _ha_exceptions_stub
sys.modules["homeassistant.components"] = MagicMock()
sys.modules["homeassistant.components.bluetooth"] = _ha_bluetooth_stub
sys.modules["homeassistant.components.bluetooth.passive_update_coordinator"] = _ha_passive_coordinator_stub
sys.modules["homeassistant.components.light"] = _ha_light_stub
sys.modules["homeassistant.helpers"] = MagicMock()
sys.modules["homeassistant.helpers.update_coordinator"] = _ha_update_coordinator_stub
sys.modules["homeassistant.helpers.entity_platform"] = _ha_entity_platform_stub


# ---------------------------------------------------------------------------
# Minimal hass fixture with a stubbed config_entries flow manager
# ---------------------------------------------------------------------------

class _FlowManager:
    """Minimal flow manager that directly invokes GoveeH6006ConfigFlow steps."""

    def __init__(self):
        self._flows: dict[str, object] = {}
        self._next_id = 1

    def _new_flow(self):
        from custom_components.govee_h6006.config_flow import GoveeH6006ConfigFlow
        flow = GoveeH6006ConfigFlow()
        flow.hass = MagicMock()
        flow._async_current_ids = lambda: set()
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = MagicMock()
        flow_id = str(self._next_id)
        self._next_id += 1
        self._flows[flow_id] = flow
        return flow_id, flow

    async def async_init(self, domain, *, context, data=None):
        flow_id, flow = self._new_flow()
        source = context.get("source", "")
        # Compare by string representation to handle MagicMock attributes
        source_str = str(source)
        if "bluetooth" in source_str.lower() or source == "bluetooth":
            result = await flow.async_step_bluetooth(data)
        elif "user" in source_str.lower() or source == "user":
            result = await flow.async_step_user(data)
        else:
            raise ValueError(f"Unsupported source: {source}")
        result["flow_id"] = flow_id
        return result

    async def async_configure(self, flow_id, user_input=None):
        flow = self._flows[flow_id]
        # After bluetooth init, we're always at bluetooth_confirm
        result = await flow.async_step_bluetooth_confirm(user_input)
        return result


class _ConfigEntriesProxy:
    def __init__(self):
        self.flow = _FlowManager()
        self.async_forward_entry_setups = AsyncMock(return_value=True)
        self.async_unload_platforms = AsyncMock(return_value=True)


class _HassStub:
    def __init__(self):
        self.config_entries = _ConfigEntriesProxy()
        self.data = {}


@pytest.fixture
def hass():
    return _HassStub()


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
