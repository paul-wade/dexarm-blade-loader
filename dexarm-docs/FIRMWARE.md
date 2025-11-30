# DexArm Custom Marlin Firmware

**IMPORTANT**: DexArm does NOT use standard Marlin. It uses a **custom fork** with DexArm-specific commands.

## Source Code

- **Repository**: https://github.com/Rotrics-Dev/Marlin_For_DexArm
- **Branch**: `DexArm_Dev`
- **Board variants**: `DexArm_3v1`, `DexArm_3v2`

---

## DexArm-Specific Commands

These commands are **NOT in standard Marlin** - they are custom to DexArm:

### Initialization Commands

| Command | Description | Standard Marlin? |
|---------|-------------|------------------|
| `M1112` | Go to HOME position (X0 Y300 Z0) | ❌ Custom |
| `M1111` | Move to recalibration position | ❌ Custom |
| `M1113` | Execute M1111 then M1112 | ❌ Custom |

### Encoder Commands (Teach & Play)

| Command | Description | Standard Marlin? |
|---------|-------------|------------------|
| `M889` | Set calibration position from encoder | ❌ Custom |
| `M890` | Get raw encoder readings | ❌ Custom |
| `M893` | Read encoder position (returns M894 X Y Z) | ❌ Custom |
| `M894 X Y Z` | Move to encoder position | ❌ Custom |
| `M895` | Read encoder → Cartesian conversion | ❌ Custom |

### Pneumatic Module

| Command | Description | Standard Marlin? |
|---------|-------------|------------------|
| `M1000` | Pump IN (suction pick / gripper release) | ❌ Custom |
| `M1001` | Pump OUT (suction release / gripper pick) | ❌ Custom |
| `M1002` | Release air pressure (neutral) | ❌ Custom |
| `M1003` | Stop pump | ❌ Custom |

### Module Selection

| Command | Description | Standard Marlin? |
|---------|-------------|------------------|
| `M888 P0` | Pen holder module | ❌ Custom |
| `M888 P1` | Laser module | ❌ Custom |
| `M888 P2` | Pneumatic module | ❌ Custom |
| `M888 P3` | 3D printing module | ❌ Custom |
| `M888 P6` | Rotary module | ❌ Custom |

### Motion Mode

| Command | Description | Standard Marlin? |
|---------|-------------|------------------|
| `M2000` | Switch G0 to linear movement | ❌ Custom |
| `M2001` | Switch G0 to rapid movement | ❌ Custom |

### Conveyor Belt

| Command | Description | Standard Marlin? |
|---------|-------------|------------------|
| `M2012 F<speed> D<dir>` | Start conveyor belt | ❌ Custom |
| `M2013` | Stop conveyor belt | ❌ Custom |
| `M2014` | Check belt status | ❌ Custom |

### Sliding Rail

| Command | Description | Standard Marlin? |
|---------|-------------|------------------|
| `M2005` | Home E-axis (sliding rail) | ❌ Custom |
| `M2006` | Check rail home status | ❌ Custom |

### Rotary Module

| Command | Description | Standard Marlin? |
|---------|-------------|------------------|
| `M2100` | Initialize rotary module | ❌ Custom |
| `M2101` | Rotary control (R/P/S params) | ❌ Custom |
| `M2103` | Get rotary firmware version | ❌ Custom |

### System Commands

| Command | Description | Standard Marlin? |
|---------|-------------|------------------|
| `M2007` | Reboot DexArm | ❌ Custom |
| `M2002`+`M2003` | Enter bootloader | ❌ Custom |

### Color Sensor (Conveyor)

| Command | Description |
|---------|-------------|
| `M1115` | Item detected |
| `M1116` | Red detected |
| `M1117` | Green detected |
| `M1118` | Blue detected |
| `M1119` | Yellow detected |

---

## Custom G28 Behavior

DexArm's G28 is **different from standard Marlin**:

```gcode
G28       ; Go to X0 Y300 Z0 (similar to M1112)
G28 C     ; Home C axis (Z) using TMC2209 stallguard
G28 Z     ; Same as G28 C
G28 B     ; Home B axis (Y) using TMC2209 stallguard  
G28 Y     ; Same as G28 B
G28 A     ; Home A axis (X) using TMC2209 stallguard
G28 X     ; Same as G28 A
```

**Order matters**: Home C/Z before AB/XY!

---

## Coordinate System

DexArm uses a **cylindrical-to-Cartesian** mapping:

```
Internal axes: A, B, C (joint angles)
External axes: X, Y, Z (Cartesian)

        +Y (forward, away from base)
         ↑
         │   HOME = (0, 300, 0)
         │
  ───────┼───────→ +X (right)
         │
        BASE

+Z = up (away from work surface)
```

---

## Standard Marlin Commands (Also Supported)

These standard Marlin commands work on DexArm:

| Command | Description |
|---------|-------------|
| `G0/G1` | Linear movement |
| `G4` | Dwell (P=ms, S=sec) |
| `G90` | Absolute positioning |
| `G91` | Relative positioning |
| `G92` | Set position |
| `M17` | Enable motors |
| `M84` | Disable motors |
| `M104/M109` | Set hotend temp |
| `M105` | Get temperature |
| `M106/M107` | Fan control |
| `M112` | Emergency stop ⚠️ |
| `M114` | Get position |
| `M204` | Set acceleration |
| `M400` | Wait for moves |
| `M410` | Quickstop |
| `M500-M503` | EEPROM settings |

---

## TMC2209 Stallguard

DexArm uses TMC2209 drivers with stallguard for:
- Axis homing without endstops
- Stall detection
- Current control (`M906`)

---

## Building Firmware

Requirements:
- Arduino IDE 1.8.8+ (NOT 2.x!)
- PlatformIO (recommended)

```bash
git clone https://github.com/Rotrics-Dev/Marlin_For_DexArm.git
cd Marlin_For_DexArm
git checkout DexArm_Dev

# Build with PlatformIO
pio run -e DexArm
```
