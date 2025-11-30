# DexArm G-Code Command Reference

Complete reference for all DexArm commands, organized by category.

---

## Table of Contents

- [Initialization](#initialization)
- [Motion Control](#motion-control)
- [Position & Modes](#position--modes)
- [Pneumatic Module](#pneumatic-module)
- [Motor Control](#motor-control)
- [Stop Commands](#stop-commands)
- [Encoder Commands](#encoder-commands)
- [Module Selection](#module-selection)
- [Laser Module](#laser-module)
- [3D Printing](#3d-printing)
- [Conveyor Belt](#conveyor-belt)
- [Rotary Module](#rotary-module)
- [Sliding Rail](#sliding-rail)
- [System Commands](#system-commands)

---

## Initialization

### M1112 - Go Home
**ALWAYS CALL FIRST after power on or connection.**

```gcode
M1112
```

- Moves arm to home position: X=0, Y=300, Z=0
- Enables motors
- **WARNING**: Do NOT confuse with M112 (emergency stop)!

### M1111 - Move to Recalibration Position

```gcode
M1111
```

- Moves arm to the recalibration position
- Used before M889 for initial calibration

### M1113 - Full Recalibration Sequence

```gcode
M1113
```

- Executes M1111 first, then M1112
- Complete initialization sequence

---

## Motion Control

### G0 - Rapid Movement

```gcode
G0 [X<pos>] [Y<pos>] [Z<pos>] [E<pos>] [F<feedrate>]
```

| Parameter | Description | Default |
|-----------|-------------|---------|
| X | X position in mm | unchanged |
| Y | Y position in mm | unchanged |
| Z | Z position in mm | unchanged |
| E | Extruder/4th axis in mm | unchanged |
| F | Feedrate in mm/min | 2400 (40mm/s) |

**Note**: Use M2000/M2001 to switch G0 between linear and rapid mode.

### G1 - Linear Movement

```gcode
G1 [X<pos>] [Y<pos>] [Z<pos>] [E<pos>] [F<feedrate>]
```

Same parameters as G0. Always moves in a straight line.

**Examples:**

```gcode
G1 F3000 X100 Y250 Z50      ; Move to position at 3000mm/min
G1 Z0                        ; Lower Z to 0 (keep X,Y)
G1 X0 Y300                   ; Move to X=0, Y=300 (keep Z)
```

### M2000 - Switch G0 to Linear Mode

```gcode
M2000
```

Makes G0 behave like G1 (straight line movement).

### M2001 - Switch G0 to Rapid Mode

```gcode
M2001
```

Makes G0 use rapid movement (faster but not straight line).

### G4 - Dwell (Wait)

```gcode
G4 P<milliseconds>    ; Wait in milliseconds
G4 S<seconds>         ; Wait in seconds
```

**Examples:**

```gcode
G4 P500     ; Wait 500ms
G4 S2       ; Wait 2 seconds
```

### M400 - Wait for Moves to Complete

```gcode
M400
```

Blocks until all queued moves finish. **Always use before reading position!**

---

## Position & Modes

### M114 - Get Current Position

```gcode
M114
```

**Response format:**

```
X:100.00 Y:250.00 Z:50.00 E:0.00
DEXARM Theta:A:45.00 B:30.00 C:10.00
ok
```

### G90 - Absolute Positioning Mode

```gcode
G90
```

All coordinates are absolute. **This is the default and recommended mode.**

```gcode
G90
G1 X100      ; Moves TO X=100
```

### G91 - Relative Positioning Mode

```gcode
G91
```

All coordinates are relative to current position.

```gcode
G91
G1 X10       ; Moves +10mm in X direction
G90          ; Always switch back to absolute!
```

### G92 - Set Work Origin

```gcode
G92 X0 Y0 Z0 E0
```

Sets current position as the new origin (0,0,0).

### G92.1 - Reset Work Origin

```gcode
G92.1
```

Resets to machine coordinate system (cancels G92).

### M204 - Set Acceleration

```gcode
M204 [P<accel>] [R<retract>] [T<travel>]
```

| Parameter | Description | Default |
|-----------|-------------|---------|
| P | Printing acceleration | 200 |
| R | Retract acceleration | 60 |
| T | Travel acceleration | 200 |

```gcode
M204               ; Read current values
M204 P300 T300     ; Set print and travel to 300
```

---

## Pneumatic Module

**IMPORTANT**: Suction cup and soft gripper use OPPOSITE commands!

### Suction Cup (Air Picker)

| Action | Command | Description |
|--------|---------|-------------|
| Pick | `M1000` | Pump IN - creates suction |
| Release | `M1001` | Pump OUT - blows air |
| Neutral | `M1002` | Release pressure |
| Stop | `M1003` | Stop pump motor |

### Soft Gripper (OPPOSITE!)

| Action | Command | Description |
|--------|---------|-------------|
| Grip | `M1001` | Pump OUT - closes gripper |
| Release | `M1000` | Pump IN - opens gripper |
| Neutral | `M1002` | Release pressure |
| Stop | `M1003` | Stop pump motor |

### Recommended Suction Sequence

```gcode
; PICK
M1000           ; Start suction
G4 P300         ; Wait 300ms for vacuum
G1 Z50          ; Lift

; PLACE  
G1 Z0           ; Lower
M1002           ; Release pressure
G4 P200         ; Wait for release
M1003           ; Stop pump
G1 Z50          ; Lift away
```

---

## Motor Control

### M84 - Disable Motors (Teach Mode)

```gcode
M84
```

Disables all motors. Arm can be moved freely by hand.
**Use for teach & play recording.**

### M17 - Enable Motors

```gcode
M17
```

Enables and locks all motors. Arm holds position.

---

## Stop Commands

### M410 - Quickstop

```gcode
M410
```

- Immediately stops all motion
- **Can resume** with G0/G1 commands
- Use for pause/interrupt

### M112 - Emergency Stop

```gcode
M112
```

- **FULL EMERGENCY STOP**
- Arm will NOT respond to any commands
- **Requires power cycle or M2007 to recover**
- Do NOT confuse with M1112 (home)!

---

## Encoder Commands

Used for teach & play functionality. **DO NOT use for general movement!**

### M893 - Read Encoder Position

```gcode
M893
```

**Response:**

```
M894 X1234 Y5678 Z9012
ok
```

Returns raw encoder values (NOT Cartesian coordinates!).

### M894 - Move to Encoder Position

```gcode
M894 X<enc_x> Y<enc_y> Z<enc_z>
```

Moves to position using encoder values from M893.

**Example teach & play:**

```gcode
M84                 ; Enable free move
; User moves arm to position
M17                 ; Lock arm
M893                ; Read encoder -> M894 X1234 Y5678 Z9012
; Save "M894 X1234 Y5678 Z9012"

; Later, to replay:
M894 X1234 Y5678 Z9012
```

### M895 - Get Cartesian from Encoder

```gcode
M895
```

Reads encoder and converts to Cartesian coordinates.

### M889 - Set Calibration Position

```gcode
M889
```

Sets current encoder position as the calibration reference.
**Only use during initial calibration procedure!**

### M890 - Get Raw Encoder Readings

```gcode
M890
```

Returns raw magnet sensor values.

---

## Module Selection

### M888 - Set/Get Front-end Module

**Set module:**

```gcode
M888 P<type>
```

| Type | Module | Offset Applied |
|------|--------|----------------|
| P0 | Pen holder | Pen offset |
| P1 | Laser | Laser offset |
| P2 | Pneumatic | Suction/gripper offset |
| P3 | 3D printing | Hotend offset |
| P6 | Rotary module | Rotary offset |

**Get current module:**

```gcode
M888
```

Response: `PEN`, `LASER`, `PUMP`, or `3D`

---

## Laser Module

### M3 - Laser On

```gcode
M3 S<power>
```

| Power | Description |
|-------|-------------|
| S0 | Off |
| S1 | Very low (for borders) |
| S255 | Maximum |

```gcode
M3 S100     ; 40% power
```

### M5 - Laser Off

```gcode
M5
```

### M6 - Get Laser Status

```gcode
M6
```

---

## 3D Printing

### M104 - Set Hotend Temperature (no wait)

```gcode
M104 S<temp>
```

```gcode
M104 S200   ; Set to 200°C, continue immediately
```

### M109 - Set Hotend Temperature (wait)

```gcode
M109 S<temp>
```

```gcode
M109 S200   ; Set to 200°C, wait until reached
```

### M105 - Get Temperature

```gcode
M105
```

### M106 - Set Fan Speed

```gcode
M106 S<speed>   ; 0-255
```

### M107 - Fan Off

```gcode
M107
```

---

## Conveyor Belt

### M2012 - Start Belt

```gcode
M2012 F<speed> D<direction>
```

| Parameter | Description |
|-----------|-------------|
| F | Speed in mm/min |
| D0 | Clockwise |
| D1 | Counter-clockwise |

```gcode
M2012 F1000 D0    ; 1000mm/min clockwise
```

### M2013 - Stop Belt

```gcode
M2013
```

### M2014 - Get Belt Status

```gcode
M2014
```

### M1115-M1119 - Color Sensor

```gcode
M1115    ; Check for item presence
M1116    ; Red detected
M1117    ; Green detected
M1118    ; Blue detected
M1119    ; Yellow detected
```

---

## Rotary Module

### M2100 - Initialize Rotary

```gcode
M2100
```

### M2101 - Rotary Control

```gcode
M2101           ; Get current angle
M2101 R<deg>    ; Relative rotation (can be >360)
M2101 P<angle>  ; Absolute position (0-360)
M2101 S<speed>  ; Continuous rotation (0-100, negative=CCW)
```

**Examples:**

```gcode
M2101 R90      ; Rotate 90° clockwise
M2101 R-45     ; Rotate 45° counter-clockwise
M2101 P180     ; Go to 180° absolute
M2101 S50      ; Spin at 50% speed
M2101 S0       ; Stop spinning
```

---

## Sliding Rail

### M2005 - Initialize Sliding Rail

```gcode
M2005 [X<max_speed>] [Y<min_speed>] [Z<thresh1>] [E<thresh2>]
```

Homes the E-axis (sliding rail) using TMC stallguard.

Default: `M2005 X30 Y10 Z60 E60`

### M2006 - Check Rail Home Status

```gcode
M2006
```

---

## System Commands

### M2007 - Reboot DexArm

```gcode
M2007
```

Software reboot. Use to recover from M112 emergency stop.

### M2002, M2003 - Enter Bootloader

```gcode
M2002
M2003
```

Sequence to enter firmware upgrade mode.

### M500 - Save Settings to EEPROM

```gcode
M500
```

### M501 - Load Settings from EEPROM

```gcode
M501
```

### M502 - Factory Reset

```gcode
M502
```

### M503 - Report All Settings

```gcode
M503
```

### G20 - Set Units to Inches

```gcode
G20
```

### G21 - Set Units to Millimeters

```gcode
G21
```

(Default is millimeters)
