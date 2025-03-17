# BLE Camera Power-On Protocol

## Overview

This document describes a generic Bluetooth Low Energy (BLE) power-on procedure for cameras, based on the Olympus Air A01 implementation. The protocol involves two primary steps:
1. Passcode Authentication (if required)
2. Power-on Instruction

## Prerequisites

- Bluetooth Low Energy (BLE) capability
- Camera's specific Characteristic UUID
- Camera's BLE device address
- (Optional) Camera's passcode

## Protocol Details

### 1. Passcode Authentication

#### Byte Sequence Structure
```
01 01 09 0c 01 02 AA BB CC DD EE FF ss 00
```

- First 6 bytes: Fixed protocol header
- Next 6 bytes (AA BB CC DD EE FF): Passcode characters
- `ss`: Checksum byte
- Last byte: Termination byte

#### Checksum Calculation
Calculate checksum by summing:
- `0x0c` (initial value)
- `0x01`
- `0x02`
- Passcode character bytes

##### Example Checksum Calculation
For passcode "123456":
```python
checksum = 0x0c + 0x01 + 0x02
for char in passcode:
    checksum += ord(char)
final_checksum = checksum & 0xFF  # Ensure 8-bit value
```

### 2. Power-on Instruction

#### Byte Sequence Structure
```
01 01 04 0f 01 01 02 13 00
```

- Fixed sequence to signal power-on
- Includes a hardcoded checksum byte (`0x13`)

## Implementation Considerations

### Bluetooth Communication
- Use a BLE library (e.g., `bleak` for Python)
- Identify correct Characteristic UUID
- Ensure proper device connection

### Timing
- Add a delay (recommended 2.5 seconds) between passcode and power-on instruction
- Handle potential connection and communication errors

## Python Implementation Template

```python
import asyncio
import bleak

class CameraPowerOn:
    def __init__(self, device_address, passcode=None):
        self.device_address = device_address
        self.passcode = passcode
        self.characteristic_uuid = "YOUR_CHARACTERISTIC_UUID"

    async def generate_passcode_bytes(self):
        # Implement passcode byte generation with checksum
        pass

    async def generate_power_on_bytes(self):
        # Implement power-on instruction bytes
        pass

    async def power_on_camera(self):
        async with bleak.BleakClient(self.device_address) as client:
            # Authenticate (if passcode required)
            if self.passcode:
                passcode_bytes = await self.generate_passcode_bytes()
                await client.write_gatt_char(self.characteristic_uuid, passcode_bytes)
                await asyncio.sleep(2.5)  # Recommended delay
            
            # Send power-on instruction
            power_on_bytes = await self.generate_power_on_bytes()
            await client.write_gatt_char(self.characteristic_uuid, power_on_bytes)
```

## Troubleshooting

- Verify BLE device address
- Check characteristic UUID
- Ensure correct passcode format
- Handle potential Bluetooth communication errors
- Log all communication attempts

## Security Considerations

- Protect passcode storage
- Use secure communication channels
- Implement error handling for authentication failures

## References

- [Original Olympus Air A01 BLE Power-on Protocol](https://github.com/your-reference-link)
- Bluetooth Low Energy Specification
- Camera-specific communication protocols

## Disclaimer

This protocol is reverse-engineered and may vary between camera models. Always refer to official documentation when available.
