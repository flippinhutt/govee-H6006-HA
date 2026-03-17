# BLE Protocol Sniffing Tutorial

This guide explains how to capture and analyze Bluetooth Low Energy (BLE) communication to reverse engineer device protocols. This is essential when adding support for new Govee models or other BLE devices.

## Table of Contents

- [Prerequisites](#prerequisites)
- [BLE Basics](#ble-basics)
- [Method 1: nRF Connect Mobile App (Easiest)](#method-1-nrf-connect-mobile-app-easiest)
- [Method 2: Android HCI Snoop Log](#method-2-android-hci-snoop-log)
- [Method 3: Linux btmon (Advanced)](#method-3-linux-btmon-advanced)
- [Method 4: Wireshark with Bluetooth Adapter](#method-4-wireshark-with-bluetooth-adapter)
- [Method 5: Ubertooth Hardware Sniffer (Expert)](#method-5-ubertooth-hardware-sniffer-expert)
- [Analyzing Captured Data](#analyzing-captured-data)
- [Protocol Reverse Engineering Workflow](#protocol-reverse-engineering-workflow)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Hardware

You'll need at least one of the following:

- **Mobile device** (Android or iOS) for nRF Connect method
- **Android device** with Developer Options enabled for HCI snoop method
- **Linux computer** with Bluetooth adapter for btmon method
- **Bluetooth 4.0+ USB adapter** for Wireshark method
- **Ubertooth One** hardware sniffer for passive monitoring (advanced)

### Software

Install based on your chosen method:

- **nRF Connect** (iOS/Android): [Download from app stores](https://www.nordicsemi.com/Products/Development-tools/nRF-Connect-for-mobile)
- **Wireshark**: `sudo apt install wireshark` or download from [wireshark.org](https://www.wireshark.org/)
- **BlueZ tools** (Linux): Usually pre-installed on modern Linux distros
- **ADB** (for Android method): `sudo apt install android-tools-adb`

### Knowledge Requirements

- Basic understanding of hexadecimal notation
- Familiarity with Bluetooth terminology (GATT, characteristics, UUIDs)
- Patience! BLE reverse engineering is an iterative process

## BLE Basics

Before diving into packet capture, understand these core concepts:

### GATT (Generic Attribute Profile)

BLE devices expose data through a hierarchical structure:

```
Service (UUID: e.g., 0000180a-0000-1000-8000-00805f9b34fb)
  └─ Characteristic (UUID: e.g., 00002a29-0000-1000-8000-00805f9b34fb)
       ├─ Properties: READ, WRITE, NOTIFY
       └─ Value: The actual data bytes
```

### Key Characteristics for Govee Devices

Most Govee devices use **custom UUIDs** like:
- Write characteristic: `00010203-0405-0607-0809-0a0b0c0d2b11`
- Read/Notify characteristic: `00010203-0405-0607-0809-0a0b0c0d2b10`

### Common BLE Operations

- **Write**: Send a command to the device (e.g., "turn on")
- **Read**: Request current value from the device
- **Notify**: Device pushes updates when its state changes
- **Indicate**: Like Notify, but with acknowledgment

## Method 1: nRF Connect Mobile App (Easiest)

**Best for:** Beginners, quick exploration, simple devices

**Pros:**
- User-friendly interface
- No computer required
- Real-time GATT exploration
- Built-in logging

**Cons:**
- Limited to devices you can pair with
- Cannot capture other app's traffic
- Manual logging required

### Step-by-Step Instructions

#### 1. Install nRF Connect

Download from your device's app store:
- **iOS**: Search "nRF Connect" in App Store
- **Android**: Search "nRF Connect" in Google Play Store

#### 2. Enable Bluetooth and Location

```
Settings → Bluetooth → ON
Settings → Location → ON (required on Android for BLE scanning)
```

#### 3. Scan for Your Device

1. Open nRF Connect
2. Tap **SCAN** at the bottom
3. Look for your Govee device (usually starts with `ihoment_` or `Govee_`)
4. Note the **RSSI** (signal strength) — stay close for reliable connection

**Example:**
```
Device: ihoment_H6006_A1B2
MAC: AA:BB:CC:DD:EE:FF
RSSI: -45 dBm
```

#### 4. Connect to the Device

1. Tap **CONNECT** next to your device
2. Wait for connection to establish (5-10 seconds)
3. The app will automatically enumerate all services and characteristics

#### 5. Explore GATT Services

You'll see a tree structure like:

```
Generic Access (0x1800)
  └─ Device Name (0x2A00)

Unknown Service (00010203-0405-0607-0809-0a0b0c0d1910)
  ├─ Unknown Characteristic (...2b10) [NOTIFY, READ]
  └─ Unknown Characteristic (...2b11) [WRITE]
```

**Record all UUIDs** — you'll need them later.

#### 6. Enable Notifications

1. Tap the **down arrow** icon (↓) next to characteristics with NOTIFY property
2. This subscribes to state updates from the device
3. Any incoming data will be logged automatically

#### 7. Send Test Commands

To discover the protocol, try writing to the WRITE characteristic:

1. Tap the **up arrow** icon (↑) next to the WRITE characteristic
2. Select **BYTE ARRAY** format
3. Try sending test patterns to see device response

**Example test commands:**
```
Power on attempt:  33 01 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 33
Power off attempt: 33 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 32
```

#### 8. Log Your Findings

In nRF Connect:
1. Tap the three-dot menu → **Log**
2. All read/write/notify events are recorded
3. Export the log via email or save to file

**Create a table like this:**

| Action | Direction | Hex Data |
|--------|-----------|----------|
| Power On | Write | `33 01 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 33` |
| Power On | Notify | `AA 01 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 AA` |
| Brightness 50% | Write | `33 04 80 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 B7` |

### Limitations of nRF Connect Method

- **Cannot intercept Govee app traffic**: You can only see commands you send manually
- **No passive monitoring**: You must be connected to the device
- **Manual process**: You have to type/test each command individually

For intercepting the official app's commands, use Method 2 or 3.

## Method 2: Android HCI Snoop Log

**Best for:** Capturing official app commands, reverse engineering proprietary protocols

**Pros:**
- Captures ALL Bluetooth traffic from your Android device
- Works with any app (Govee, LIFX, etc.)
- Easy to enable, no special hardware needed

**Cons:**
- Requires Android device
- Developer mode required
- Large log files (filter carefully)

### Step-by-Step Instructions

#### 1. Enable Developer Options

On your Android device:

```
Settings → About Phone → Tap "Build Number" 7 times
(You'll see a message: "You are now a developer!")
```

#### 2. Enable Bluetooth HCI Snoop Log

```
Settings → System → Developer Options → Enable Bluetooth HCI snoop log
```

**Important:** On some devices, you may need to toggle this option OFF and back ON each time before capturing.

#### 3. Clear Old Logs (Optional)

```bash
# On your computer, with device connected via USB
adb shell
rm /sdcard/Android/data/btsnoop_hci.log
exit
```

#### 4. Use the Govee App

1. Open the official **Govee Home** app
2. Control your device:
   - Turn light on/off
   - Change brightness (try specific values: 25%, 50%, 75%, 100%)
   - Set specific colors (pure red, pure green, pure blue, white)
   - Change color temperature (coolest, middle, warmest)
3. Perform each action **slowly** with 2-3 seconds between commands
4. **Document each action** with timestamps in a notebook

**Example log:**
```
10:15:30 - Power On
10:15:35 - Brightness 50%
10:15:40 - RGB: Red (255, 0, 0)
10:15:45 - RGB: Green (0, 255, 0)
10:15:50 - RGB: Blue (0, 0, 255)
10:15:55 - Color Temp: 2700K
```

#### 5. Pull the Log File

```bash
# Connect your Android device via USB
# Enable "File Transfer" mode when prompted

# Pull the log file
adb pull /sdcard/Android/data/btsnoop_hci.log ./govee_capture.log

# Verify file size (should be a few MB)
ls -lh govee_capture.log
```

**Alternative locations** (try if the above doesn't work):
```bash
adb pull /data/misc/bluetooth/logs/btsnoop_hci.log ./govee_capture.log
adb pull /sdcard/btsnoop_hci.log ./govee_capture.log
```

#### 6. Open in Wireshark

```bash
wireshark govee_capture.log
```

#### 7. Filter for Your Device

In Wireshark, apply a display filter:

```
bluetooth.addr == AA:BB:CC:DD:EE:FF
```

Replace `AA:BB:CC:DD:EE:FF` with your device's MAC address.

**Better filter for GATT writes only:**
```
bluetooth.addr == AA:BB:CC:DD:EE:FF && btatt.opcode == 0x52
```

- `0x52` = Write Command (no response)
- `0x12` = Write Request (with response)
- `0x1b` = Handle Value Notification (device → phone)

#### 8. Export Filtered Packets

```
File → Export Packet Dissections → As CSV...
```

This creates a spreadsheet of all captured packets for easy analysis.

### Parsing HCI Snoop Logs

Each GATT write will show:

```
Frame 42: 53 bytes on wire
Bluetooth HCI H4
  [Direction: Sent (0x00)]
Bluetooth HCI ACL Packet
  Connection Handle: 0x0040
Bluetooth Attribute Protocol
  Opcode: Write Command (0x52)
  Handle: 0x0025
  Value: 33010100000000000000000000000000000000
```

**The "Value" field is your command packet!**

## Method 3: Linux btmon (Advanced)

**Best for:** Real-time monitoring, Linux users, scripting

**Pros:**
- Built into most Linux distros
- Real-time packet capture
- Can capture from any Bluetooth source

**Cons:**
- Requires root access
- Complex output format
- Must have BLE adapter on Linux machine

### Step-by-Step Instructions

#### 1. Install BlueZ Tools (if not installed)

```bash
# Debian/Ubuntu
sudo apt install bluez

# Fedora
sudo dnf install bluez

# Verify installation
btmon --version
```

#### 2. Start btmon in Capture Mode

```bash
# Capture to file
sudo btmon -w govee_capture.snoop

# Or capture with live output
sudo btmon | tee btmon_output.txt
```

**Tip:** Open two terminals — one for `btmon`, one for `bluetoothctl` to control the device.

#### 3. Connect to Your Device

In a second terminal:

```bash
bluetoothctl
[bluetooth]# scan on
# Wait for your device to appear
[bluetooth]# scan off
[bluetooth]# connect AA:BB:CC:DD:EE:FF
[bluetooth]# info AA:BB:CC:DD:EE:FF
```

Note the UUIDs listed in the output.

#### 4. Send Commands (via Govee app or bluetoothctl)

**Option A:** Use the Govee app on your phone while `btmon` captures

**Option B:** Use `bluetoothctl` or `gatttool`:

```bash
# Using gatttool (older method)
gatttool -b AA:BB:CC:DD:EE:FF --char-write-req -a 0x0025 -n 33010100000000000000000000000000000000

# Using bluetoothctl (modern method)
# First, find the characteristic path
bluetoothctl
[bluetooth]# menu gatt
[bluetooth]# list-attributes AA:BB:CC:DD:EE:FF
# Note the characteristic path (e.g., /org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF/service0010/char0011)
[bluetooth]# select-attribute /org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF/service0010/char0011
[bluetooth]# write 0x33 0x01 0x01 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x00 0x33
```

#### 5. Stop btmon

Press `Ctrl+C` to stop the capture.

#### 6. Analyze the Capture

Open the `.snoop` file in Wireshark:

```bash
wireshark govee_capture.snoop
```

Or parse btmon output with grep:

```bash
# Find all ATT Write Commands
grep "ATT: Write Command" btmon_output.txt -A 5

# Find all Handle Value Notifications
grep "Handle Value Notification" btmon_output.txt -A 5
```

### Example btmon Output

```
> ACL Data TX: Handle 64 flags 0x00 dlen 23
  ATT: Write Command (0x52) len 18
    Handle: 0x0025
      Data: 33010100000000000000000000000000000000
< ACL Data RX: Handle 64 flags 0x02 dlen 25
  ATT: Handle Value Notification (0x1b) len 20
    Handle: 0x0024
      Data: aa010100000000000000000000000000000000
```

- `>` = Sent to device (TX)
- `<` = Received from device (RX)
- `Handle: 0x0025` = Write characteristic handle
- `Handle: 0x0024` = Notify characteristic handle
- `Data:` = The actual packet bytes

## Method 4: Wireshark with Bluetooth Adapter

**Best for:** Passive monitoring without connecting to the device

**Pros:**
- Can monitor connections between other devices (e.g., phone ↔ bulb)
- No need to connect to the device yourself
- Full packet capture with timing information

**Cons:**
- Requires compatible Bluetooth adapter
- Cannot decrypt encrypted connections
- May miss packets if not on the same Bluetooth channel

### Step-by-Step Instructions

#### 1. Install Wireshark

```bash
# Linux
sudo apt install wireshark

# macOS (note: Bluetooth capture support is limited)
brew install wireshark

# Add your user to wireshark group (Linux)
sudo usermod -aG wireshark $USER
# Log out and back in for group changes to take effect
```

#### 2. Check Adapter Support

```bash
# List available interfaces
wireshark -D

# Look for "bluetooth-monitor" or "bluetooth0"
```

**If you don't see a Bluetooth interface:**
- On Linux: `sudo modprobe btusb`
- You may need to install `bluez-hcidump`

#### 3. Start Capture

```bash
# Command-line capture
sudo wireshark

# In Wireshark GUI:
# 1. Select "Bluetooth HCI H4" or "bluetooth-monitor" interface
# 2. Click the blue shark fin icon to start capture
```

#### 4. Perform Actions on Device

Use the Govee app or another phone to control the device while Wireshark captures packets.

#### 5. Filter Relevant Packets

Apply display filters:

```
# All BLE ATT protocol packets
btatt

# Only GATT writes
btatt.opcode == 0x52 || btatt.opcode == 0x12

# Only notifications
btatt.opcode == 0x1b

# Specific device (if you know the connection handle)
bthci_acl.chandle == 0x0040
```

#### 6. Export Captured Data

```
File → Export Packet Dissections → As JSON/CSV/XML
```

### Troubleshooting Wireshark Method

**Problem:** No Bluetooth interface available

**Solution:**
```bash
# Ensure Bluetooth monitor is loaded
sudo modprobe btmon
# Or use btmon to capture and pipe to Wireshark
sudo btmon -w - | wireshark -k -i -
```

**Problem:** Seeing packets but they're encrypted

**Solution:** BLE encryption cannot be decrypted without the pairing keys. Use Method 2 (HCI snoop) to capture from the paired device itself.

## Method 5: Ubertooth Hardware Sniffer (Expert)

**Best for:** Passive monitoring, protocol research, encrypted connections

**Pros:**
- True passive sniffing (device has no idea it's being monitored)
- Can capture advertising packets
- Can capture connections between two devices you don't control

**Cons:**
- Requires Ubertooth One hardware (~$120 USD)
- Complex setup
- Cannot decrypt encrypted connections without pairing keys

### Hardware Required

- **Ubertooth One**: Available from [Great Scott Gadgets](https://greatscottgadgets.com/ubertoothone/)

### Step-by-Step Instructions

#### 1. Install Ubertooth Tools

```bash
# Debian/Ubuntu
sudo apt install ubertooth

# Build from source
git clone https://github.com/greatscottgadgets/ubertooth.git
cd ubertooth/host
mkdir build && cd build
cmake ..
make
sudo make install
```

#### 2. Update Ubertooth Firmware

```bash
ubertooth-util -v  # Check version
ubertooth-util -f  # Flash latest firmware
```

#### 3. Start Sniffing BLE Advertisements

```bash
ubertooth-btle -f

# Pipe to Wireshark
ubertooth-btle -f -c govee_capture.pcap
```

#### 4. Follow a Connection

```bash
# First, find the device's advertising address
ubertooth-btle -f | grep "ihoment"

# Note the address (e.g., aa:bb:cc:dd:ee:ff)

# Follow a connection (experimental)
ubertooth-btle -f -t AA:BB:CC:DD:EE:FF
```

#### 5. Analyze in Wireshark

```bash
wireshark govee_capture.pcap
```

**Note:** Ubertooth is primarily useful for capturing advertising packets and unencrypted connections. Most Govee devices use pairing/encryption, which makes passive decryption difficult.

### When to Use Ubertooth

- Research into BLE advertising formats
- Capturing device discovery behavior
- Investigating devices that don't require pairing
- Advanced reverse engineering projects

For most Govee reverse engineering, **Method 2 (Android HCI Snoop)** is more practical.

## Analyzing Captured Data

Once you have captured packets, analyze them systematically.

### Step 1: Identify Packet Structure

Look for patterns in the hex data:

```
33 01 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 33  # Power ON
33 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 32  # Power OFF
33 04 80 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 B7  # Brightness 128
```

**Ask yourself:**
- What bytes change between commands?
- Is there a consistent length? (Govee uses 20 bytes)
- Is there a header/head byte? (Govee uses `0x33`)
- Is there a checksum? (Govee uses XOR in the last byte)

### Step 2: Decode Each Field

Create a table:

| Position | Name | Description | Example Values |
|----------|------|-------------|----------------|
| Byte 0 | Head | Command type identifier | `0x33` (command), `0xAA` (query) |
| Byte 1 | Command | Specific command ID | `0x01` (power), `0x04` (brightness), `0x05` (color) |
| Byte 2-18 | Payload | Command-specific data | Varies |
| Byte 19 | Checksum | XOR of bytes 0-18 | Calculated |

### Step 3: Identify Checksums

Test common checksum algorithms:

**XOR Checksum (used by Govee H6006):**
```python
def verify_xor_checksum(packet):
    xor = 0
    for byte in packet[:-1]:  # All bytes except last
        xor ^= byte
    return (xor & 0xFF) == packet[-1]

# Test with a captured packet
packet = bytes.fromhex("33010100000000000000000000000000000033")
print(verify_xor_checksum(packet))  # Should print True
```

**Sum Checksum (modulo 256):**
```python
def verify_sum_checksum(packet):
    checksum = sum(packet[:-1]) & 0xFF
    return checksum == packet[-1]
```

**CRC (more complex):**
- Try `crc8`, `crc16`, `crc32` from libraries like `crcmod`

### Step 4: Reverse Engineer Color Encoding

**RGB Color:**
Look for patterns when you sent pure red (255,0,0), pure green (0,255,0), pure blue (0,0,255):

```
Red:   33 05 02 FF 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ??
Green: 33 05 02 00 FF 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ??
Blue:  33 05 02 00 00 FF 00 00 00 00 00 00 00 00 00 00 00 00 00 ??
```

Pattern identified: `33 05 02 R G B ...`

**Color Temperature:**
Try different kelvin values and look for patterns:

```
2700K: 33 05 02 FF FF FF 01 FF 00 00 00 00 00 00 00 00 00 00 00 ??
4000K: 33 05 02 FF FF FF 01 99 66 00 00 00 00 00 00 00 00 00 00 ??
6500K: 33 05 02 FF FF FF 01 00 FF 00 00 00 00 00 00 00 00 00 00 ??
```

Note that byte 6 + byte 7 = 255 (complementary). This is the warm/cold ratio.

### Step 5: Document Your Findings

Create a protocol specification document:

```markdown
# Govee H7021 Protocol Specification

## Packet Format

- Length: 20 bytes
- Checksum: Sum of bytes 0-18, modulo 256, in byte 19

## Commands

### Power (0x01)

Format: `33 01 [state] 00 00 00 ... [checksum]`
- state: 0x01 = on, 0x00 = off

### Brightness (0x04)

Format: `33 04 [value] 00 00 00 ... [checksum]`
- value: 0-255 (0-100% brightness)

### RGB Color (0x05)

Format: `33 05 02 [R] [G] [B] 00 00 00 ... [checksum]`
- R, G, B: 0-255

## GATT Characteristics

- Write UUID: `00010203-0405-0607-0809-0a0b0c0d3b11`
- Notify UUID: `00010203-0405-0607-0809-0a0b0c0d3b10`
```

## Protocol Reverse Engineering Workflow

Follow this systematic approach:

### Phase 1: Discovery (Day 1)

1. **Scan** for device with nRF Connect
2. **Record** all service/characteristic UUIDs
3. **Test** basic connectivity (read/write permissions)
4. **Enable** notifications on all readable characteristics
5. **Document** device info (model, firmware version, manufacturer)

### Phase 2: Command Capture (Days 2-3)

1. **Set up** Android HCI snoop or btmon
2. **Perform** each action in the official app:
   - Power on/off
   - Brightness at specific values (0%, 25%, 50%, 75%, 100%)
   - Each color mode (RGB, white, color temp)
   - Any special effects or scenes
3. **Log** each action with timestamp
4. **Pull** capture file and open in Wireshark
5. **Export** packets to CSV for analysis

### Phase 3: Pattern Recognition (Days 3-4)

1. **Align** timestamps from your log with packets in Wireshark
2. **Compare** similar commands (e.g., different brightness values)
3. **Identify** which bytes change and which stay constant
4. **Calculate** checksums to find the algorithm
5. **Test** hypotheses by manually sending crafted packets via nRF Connect

### Phase 4: Validation (Day 5)

1. **Write** a Python script to build packets:
   ```python
   def build_power_command(on):
       cmd = [0x33, 0x01, 0x01 if on else 0x00]
       cmd += [0] * (19 - len(cmd))
       checksum = 0
       for b in cmd:
           checksum ^= b
       cmd.append(checksum & 0xFF)
       return bytes(cmd)
   ```
2. **Test** script output against known-good captured packets
3. **Send** script-generated packets via nRF Connect or bluetoothctl
4. **Verify** device responds correctly
5. **Iterate** until all commands work reliably

### Phase 5: Documentation (Day 6)

1. **Write** protocol specification
2. **Create** packet builder code for the integration
3. **Add** tests for each command type
4. **Document** any edge cases or gotchas
5. **Submit** contribution to the project

## Troubleshooting

### Problem: Cannot connect to device

**Symptoms:** Connection times out or fails immediately

**Solutions:**
1. Ensure no other app is connected (close Govee app)
2. Turn Bluetooth off and on
3. Move closer to the device (RSSI > -70 dBm)
4. Try resetting the device (power cycle)
5. On Android: Clear Bluetooth cache
   ```
   Settings → Apps → Bluetooth → Storage → Clear Cache
   ```

### Problem: No HCI snoop file found

**Symptoms:** `adb pull` returns "file not found"

**Solutions:**
1. Check if Developer Options are enabled
2. Toggle HCI snoop log OFF and back ON
3. Try alternative file paths:
   ```bash
   adb pull /data/misc/bluetooth/logs/btsnoop_hci.log
   adb pull /data/log/bt/btsnoop_hci.log
   adb pull /sdcard/btsnoop_hci.log
   ```
4. Some Samsung devices:
   ```bash
   adb pull /data/log/bt/snoop/btsnoop_hci.log
   ```
5. Use `adb shell` and search:
   ```bash
   adb shell
   find / -name "btsnoop*" 2>/dev/null
   ```

### Problem: Wireshark shows encrypted packets

**Symptoms:** Packet contents show as "Encrypted" or gibberish

**Explanation:** BLE connections can use encryption after pairing.

**Solutions:**
- Use **Android HCI snoop** instead (captures before encryption on the host side)
- Or use **btmon** on Linux if your machine is the connected device
- Passive sniffing (Ubertooth) cannot decrypt without pairing keys

### Problem: Cannot identify packet structure

**Symptoms:** Packets seem random, no clear pattern

**Checklist:**
1. **Verify packet length** — is it always the same?
2. **Look at multiple samples** — perform the same action 3+ times
3. **Compare minimal pairs** — change only one parameter at a time
4. **Check for timestamps** — some devices embed timestamps in packets
5. **Consider encoding** — some devices use base64 or other encoding
6. **Test known values** — send max/min values (0, 128, 255) to see extremes

### Problem: Checksum doesn't validate

**Try these algorithms:**

```python
# XOR
checksum = 0
for b in packet[:-1]:
    checksum ^= b
checksum &= 0xFF

# Sum (modulo 256)
checksum = sum(packet[:-1]) & 0xFF

# Sum (two's complement)
checksum = (~sum(packet[:-1]) + 1) & 0xFF

# CRC-8
import crcmod
crc8_func = crcmod.predefined.mkCrcFun('crc-8')
checksum = crc8_func(bytes(packet[:-1]))

# Nibble sum
checksum = sum(b >> 4 for b in packet[:-1]) + sum(b & 0x0F for b in packet[:-1])
checksum &= 0xFF
```

### Problem: Device doesn't respond to crafted packets

**Debugging steps:**

1. **Verify UUID** — ensure you're writing to the correct characteristic
2. **Check byte order** — try reversing the packet
3. **Validate length** — most BLE writes have a max length (20 or 23 bytes)
4. **Test checksum** — calculate it precisely, off-by-one errors are common
5. **Try Write Request vs Write Command:**
   - Write Request (0x12) — expects acknowledgment
   - Write Command (0x52) — no acknowledgment
   Use the same opcode as the official app
6. **Add delays** — some devices need time between commands (100-500ms)
7. **Compare hex exactly:**
   ```python
   expected = "33010100000000000000000000000000000033"
   actual   = "33010100000000000000000000000000000033"
   print(expected == actual)
   ```

### Problem: btmon shows "Permission denied"

**Solution:**
```bash
# Add user to bluetooth group
sudo usermod -aG bluetooth $USER

# Or run with sudo
sudo btmon -w capture.snoop
```

### Problem: Ubertooth not detected

**Solution:**
```bash
# Check if device is recognized
lsusb | grep Ubertooth

# Update udev rules
sudo cp ubertooth/host/libubertooth/99-ubertooth.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules

# Replug the device
```

## Next Steps

After successfully capturing and analyzing the protocol:

1. **Implement packet builders** — see [CONTRIBUTING_DEVELOPER_GUIDE.md](CONTRIBUTING_DEVELOPER_GUIDE.md)
2. **Write tests** — create unit tests for each command type
3. **Test with hardware** — validate with real device
4. **Submit PR** — contribute your work back to the project

## Reference Resources

### Official Documentation

- **Bluetooth Core Specification**: [bluetooth.com/specifications](https://www.bluetooth.com/specifications/specs/)
- **GATT Specification**: Defines the attribute protocol

### Tools

- **nRF Connect**: [nordicsemi.com/Products/Development-tools/nRF-Connect-for-mobile](https://www.nordicsemi.com/Products/Development-tools/nRF-Connect-for-mobile)
- **Wireshark**: [wireshark.org](https://www.wireshark.org/)
- **Ubertooth**: [greatscottgadgets.com/ubertoothone](https://greatscottgadgets.com/ubertoothone/)

### Community

- **Govee H6006 Integration**: [GitHub Issues](https://github.com/yourusername/govee_h6006/issues)
- **Home Assistant Community**: [community.home-assistant.io](https://community.home-assistant.io/)

### Related Guides

- [CONTRIBUTING_DEVELOPER_GUIDE.md](CONTRIBUTING_DEVELOPER_GUIDE.md) — Adding new device support
- [ARCHITECTURE.md](ARCHITECTURE.md) — Integration architecture overview
- [API.md](API.md) — API reference for packet builders

---

**Happy sniffing!** 🔍 If you discover a new protocol, please contribute your findings back to the community.
