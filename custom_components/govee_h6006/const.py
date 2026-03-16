DOMAIN = "govee_h6006"

# Legacy constants (kept for backward compatibility during transition)
DISCOVERY_NAME = "ihoment_"
WRITE_CHARACTERISTIC_UUID = "00010203-0405-0607-0809-0a0b0c0d2b11"
READ_CHARACTERISTIC_UUID = "00010203-0405-0607-0809-0a0b0c0d2b10"
MIN_KELVIN = 2700
MAX_KELVIN = 6500

# Multi-model registry mapping model identifiers to their metadata
# This is the single source of truth for supported models
MODEL_REGISTRY = {
    "H6006": {
        "name": "Govee H6006",
        "discovery_prefix": "ihoment_H6006",
        "write_uuid": "00010203-0405-0607-0809-0a0b0c0d2b11",
        "read_uuid": "00010203-0405-0607-0809-0a0b0c0d2b10",
        "min_kelvin": 2700,
        "max_kelvin": 6500,
        "protocol_class": "H6006Protocol",
        "capabilities": {
            "color_temp": True,
            "music_sync": False,
            "scene_modes": False,
        },
    },
    "H6008": {
        "name": "Govee H6008",
        "discovery_prefix": "ihoment_H6008",
        "write_uuid": "00010203-0405-0607-0809-0a0b0c0d2b11",
        "read_uuid": "00010203-0405-0607-0809-0a0b0c0d2b10",
        "min_kelvin": 2700,
        "max_kelvin": 6500,
        "protocol_class": "H6008Protocol",
        "capabilities": {
            "color_temp": True,
            "music_sync": False,
            "scene_modes": False,
        },
    },
}

# Options flow configuration constants
DEFAULT_POLLING_INTERVAL = 30
MIN_POLLING_INTERVAL = 10
MAX_POLLING_INTERVAL = 120

DEFAULT_CONNECTION_TIMEOUT = 20
MIN_CONNECTION_TIMEOUT = 5
MAX_CONNECTION_TIMEOUT = 30

DEFAULT_SUPPRESSION_WINDOW = 500
MIN_SUPPRESSION_WINDOW = 200
MAX_SUPPRESSION_WINDOW = 2000

DEFAULT_MAX_RETRIES = 5
MIN_MAX_RETRIES = 1
MAX_MAX_RETRIES = 10
MAX_RECONNECT_ATTEMPTS = 5
RECONNECT_BACKOFF_BASE = 1.0
RECONNECT_BACKOFF_MAX = 30.0
RECONNECT_COOLDOWN_SECONDS = 300  # 5 minutes - allow recovery after cooldown
