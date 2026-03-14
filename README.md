# Govee H6006 BLE Integration for Home Assistant 🏠

[![hacs](https://img.shields.io/badge/HACS-Integration-blue.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/flippinhutt/govee?sort=semver&style=for-the-badge&color=green)](https://github.com/flippinhutt/govee/releases/)
[![GitHub Release Date](https://img.shields.io/github/release-date/flippinhutt/govee?style=for-the-badge&color=green)](https://github.com/flippinhutt/govee/releases/)
![GitHub commit activity](https://img.shields.io/github/commit-activity/m/flippinhutt/govee?style=for-the-badge)

## Overview

**Control your Govee H6006 lights locally via Bluetooth — zero cloud dependency, zero API keys, zero MQTT broker.**

This Home Assistant custom integration discovers and controls Govee H6006 Bluetooth lights directly through your Home Assistant server's Bluetooth adapter. No internet connection required, no third-party services, just pure local control.

### Key Features

- **🔒 100% Local**: All communication stays on your local network via Bluetooth Low Energy (BLE)
- **⚡ Auto-Discovery**: Devices appear automatically — no manual configuration needed
- **🎨 Full Control**: Brightness, color (RGB), and on/off state
- **🚫 No Cloud**: Never talks to Govee's servers or requires API keys
- **🔌 Simple Setup**: If you have a Bluetooth adapter, you're ready to go

### Supported Devices

Currently supports:
- **Govee H6006** (advertises as `ihoment_*`)

## Installation

### HACS (Recommended)

1. Ensure [HACS](https://hacs.xyz/) is installed in Home Assistant
2. Open HACS in Home Assistant
3. Go to any of the sections (integrations, frontend, automation)
4. Click on the 3 dots in the top right corner
5. Select "Custom repositories"
6. Add the following URL: `https://github.com/flippinhutt/govee`
7. Select **Integration** as the category
8. Click the "ADD" button
9. Search for "Govee H6006 BLE"
10. Click "Download"
11. Restart Home Assistant

### Manual Installation

To install manually, download [the latest release](https://github.com/flippinhutt/govee/releases/latest/) and extract the contents to your `config/custom_components` directory:

```bash
cd /config  # or wherever your Home Assistant config directory is
mkdir -p custom_components
cd custom_components
wget https://github.com/flippinhutt/govee/releases/latest/download/govee_h6006.zip
unzip govee_h6006.zip -d govee_h6006
rm govee_h6006.zip
```

Then restart Home Assistant.

## Configuration

### Prerequisites

- **Bluetooth Adapter**: Your Home Assistant server must have a working Bluetooth adapter
- **Bluetooth Integration**: The built-in Home Assistant [Bluetooth integration](https://www.home-assistant.io/integrations/bluetooth/) must be enabled (it usually is by default on Home Assistant OS)

### Setup Steps

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=govee_h6006)

1. From the Home Assistant dashboard, go to **Settings** → **Devices & Services**
2. Click the **+ Add Integration** button in the bottom right
3. Search for "Govee H6006 BLE"
4. Select the integration from the list
5. Your Govee H6006 lights should be discovered automatically
6. Select the device you want to add and click **Submit**

That's it! Your lights will appear as standard Home Assistant light entities.

## Troubleshooting

### Devices Not Discovered

**Problem**: Your Govee H6006 lights don't appear during setup.

**Solutions**:
- **Check Bluetooth range**: BLE has limited range (~10-30 feet / 3-10 meters). Move your lights closer to the Home Assistant server or vice versa.
- **Restart the lights**: Power cycle your Govee lights by turning them off and on again at the wall switch or power adapter.
- **Check Bluetooth adapter**: Run `bluetoothctl` on your Home Assistant server and verify the adapter is working with `list` and `scan on`.
- **Interference**: 2.4GHz Wi-Fi, microwaves, and other Bluetooth devices can interfere with BLE. Try turning off nearby 2.4GHz devices temporarily.

### BLE Adapter Placement Tips

For best results:
- **Keep the Bluetooth adapter away from USB 3.0 ports and cables** — USB 3.0 generates interference in the 2.4GHz band
- **Use a USB extension cable** to position the Bluetooth adapter away from the server chassis and closer to your lights
- **Avoid metal enclosures** — if your Home Assistant server is in a metal case, the case can block BLE signals
- **Minimize obstacles** — BLE signals don't penetrate walls well, especially concrete or metal

### Connection Drops or Slow Response

**Problem**: Lights disconnect frequently or commands are slow.

**Solutions**:
- **Reduce distance**: Move the Bluetooth adapter closer to the lights
- **Check for interference**: Other BLE devices, Wi-Fi routers, and USB 3.0 devices can cause interference
- **Reduce BLE device count**: BLE adapters have a limited number of simultaneous connections (usually 3-7 devices)
- **Enable debug logging** (see below) to identify connection issues

### Enable Debug Logging

To troubleshoot issues, enable debug logging for the integration:

1. Go to **Settings** → **Devices & Services** → **Govee H6006 BLE**
2. Click **Enable debug logging**

Or add this to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.govee_h6006: debug
    bleak: debug
```

Then restart Home Assistant and check the logs under **Settings** → **System** → **Logs**.

### Device Shows as "Unavailable"

**Problem**: Device appears in Home Assistant but shows as "Unavailable".

**Solutions**:
- The device may be out of Bluetooth range
- The device may be powered off
- Another application or Bluetooth device may have connected to it
- Try reloading the integration: **Settings** → **Devices & Services** → **Govee H6006 BLE** → **⋮** → **Reload**

## Protocol Documentation

This integration uses Govee's proprietary Bluetooth Low Energy (BLE) protocol to communicate with H6006 devices. The protocol is reverse-engineered and uses BLE GATT characteristics for control.

### Technical Details

- **Service**: Uses standard BLE GATT services
- **Discovery**: Devices advertise as `ihoment_*` via BLE advertising packets
- **Commands**: Power, brightness, and RGB color are sent via GATT characteristic writes
- **State Polling**: Device state is read periodically via GATT characteristic reads

## Help and Contribution

Found a bug or have a feature request? Please [open an issue](https://github.com/flippinhutt/govee/issues) on GitHub.

### Contributing

Contributions are welcome! If you'd like to add support for additional Govee models or improve the integration:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-new-feature`)
3. Make your changes
4. Test thoroughly with a real device
5. Submit a pull request

For major changes, please open an issue first to discuss what you'd like to change.

### Adding Support for New Models

If you have a different Govee BLE device and can capture BLE traffic (using tools like Wireshark, nRF Connect, or `btmon`), please open an issue with the capture logs. This helps extend support to more devices.

## Disclaimer

This custom integration is not officially endorsed or supported by Govee.
Use it at your own risk and ensure that you comply with all relevant terms of service and privacy policies.

---

**Enjoy your locally-controlled Govee lights! 💡**
