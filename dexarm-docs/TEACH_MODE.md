# DexArm Teach Mode - Complete Guide

> **Source**: [Firmware M_dexarm.cpp](https://github.com/Rotrics-Dev/Marlin_For_DexArm/blob/master/Marlin/src/gcode/control/M_dexarm.cpp)

## Overview

Teach mode allows you to physically move the arm by hand and record positions for playback.

## Commands

| Command | Function | Response |
|---------|----------|----------|
| `M84` | Motors OFF - arm can be moved freely | `ok` |
| `M17` | Motors ON - arm locks in place | `ok` |
| `M893` | Read raw encoder values | `M894 X:nnn Y:nnn Z:nnn` |
| `M894 X Y Z` | Move to encoder position | `ok` |
| `M895` | Read encoder → Cartesian | `X:n.nn Y:n.nn Z:n.nn` |

## ⚠️ Critical: M895 vs M114

| Command | Returns | Use When |
|---------|---------|----------|
| `M114` | Last **commanded** position | After G-code moves |
| `M895` | Actual **physical** position from encoders | After teach mode / manual movement |

**After teach mode, M114 is WRONG!** It still returns the old position before you moved the arm. You MUST use M895 to get actual position.

## Firmware Implementation

From `M_dexarm.cpp`:

```cpp
// M893 - Read raw encoder
void GcodeSuite::M893(void) {
    get_current_encoder();  // Returns M894 X Y Z format
}

// M895 - Encoder to Cartesian
void GcodeSuite::M895(void) {
    xyz_pos_t position;
    get_current_position_from_position_sensor(position);
    SERIAL_ECHOLNPAIR("X:", position.x, " Y:", position.y, " Z:", position.z);
}
```

## Workflow: Recording Positions

### 1. Enter Teach Mode

```gcode
M84           ; Motors off - arm is free
```

### 2. Move Arm by Hand
Physically move the arm to desired position.

### 3. Read Position (Choose One)

**Option A: Cartesian (for our app)**

```gcode
M895          ; Returns: X:150.00 Y:280.00 Z:45.00
```

**Option B: Raw Encoder (for direct replay)**

```gcode
M893          ; Returns: M894 X1234 Y5678 Z9012
```

### 4. Exit Teach Mode

```gcode
M17           ; Motors lock at current position
```

### 5. Sync Position Tracking

```gcode
M895          ; Read actual position
              ; Update your internal tracking to match!
```

## Workflow: Replaying Positions

### Using Encoder Values (M894)

```gcode
M894 X1234 Y5678 Z9012    ; Move to recorded encoder position
```
- Pros: Exact position replay
- Cons: Can't mix with Cartesian moves, no safety checks

### Using Cartesian (G1)

```gcode
G1 X150 Y280 Z45 F2000    ; Move to Cartesian position
```
- Pros: Can use safety planning, workspace limits
- Cons: Slight precision difference from original

## Position Sync Pattern (Our App)

```python
def motors_on(self):
    """Exit teach mode and sync position."""
    self.send("M17")           # Lock motors
    self.sync_position()       # CRITICAL!

def sync_position(self):
    """Read actual position from encoders."""
    response = self.send("M895")
    pos = parse_xyz(response)  # X:n Y:n Z:n
    self._position = pos       # Update tracking
```

**Why sync is critical:**
- After teach mode, arm is at unknown position
- Internal `_position` is stale (from before teach mode)
- Any movement planning will be WRONG
- Arm will jerk unpredictably

## Common Mistakes

### ❌ Using M114 After Teach Mode
```python
# WRONG - returns old position!
self.send("M17")
response = self.send("M114")  # Still returns pre-teach position
```

### ❌ Moving Without Syncing
```python
# WRONG - will calculate wrong motion!
self.send("M17")
self.move_to(target)  # Uses stale _position for planning
```

### ✅ Correct Pattern
```python
self.send("M17")
self.sync_position()  # Read M895, update _position
self.move_to(target)  # Now motion planning is correct
```

## M896 - Teach & Play Configuration

Configure teach mode movement settings:

```gcode
M896 P0      ; Fast mode (default)
M896 P1      ; Line mode (linear interpolation)
M896 P2      ; Jump mode (lift, move, lower)
M896 H50     ; Set jump height to 50mm
M896 F50     ; Set feedrate to 50mm/s
```

## DexArm Kinematics

The arm uses a **SCARA parallel linkage** design:
- 3 rotary joints with magnetic encoders
- Inner and outer arm links
- Parallel bars maintain end-effector orientation

URDF model: [github.com/Rotrics-Dev/URDF-of-DexArm](https://github.com/Rotrics-Dev/URDF-of-DexArm/tree/main/URDF)

```text
Joint Limits:
- Base rotation: -110° to +110°
- Shoulder (B_Rot->In_1): 0° to 90°
- Elbow (Join->In_2): -34° to 69°
```

The `M895` command performs forward kinematics internally to convert encoder readings to Cartesian XYZ.
