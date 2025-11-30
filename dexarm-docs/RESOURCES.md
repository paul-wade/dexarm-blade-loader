# Official Rotrics Resources

## GitHub Repositories

All open source at [github.com/Rotrics-Dev](https://github.com/Rotrics-Dev)

| Repository | Description | Key Files |
|------------|-------------|-----------|
| [Marlin_For_DexArm](https://github.com/Rotrics-Dev/Marlin_For_DexArm) | Custom firmware | `Marlin/src/gcode/control/M_dexarm.cpp` |
| [DexArm_API](https://github.com/Rotrics-Dev/DexArm_API) | Python SDK (pydexarm) | `pydexarm/pydexarm.py` |
| [rotrics-studio-app](https://github.com/Rotrics-Dev/rotrics-studio-app) | Official desktop app | Electron + Node.js |
| [URDF-of-DexArm](https://github.com/Rotrics-Dev/URDF-of-DexArm) | Robot description + kinematics | `URDF/DexArm.urdf` |
| [DexArm_Demo](https://github.com/Rotrics-Dev/DexArm_Demo) | Example projects | Vision demos |

## Documentation

- [Official Manual](https://manual.rotrics.com/)
- [G-code API Reference](https://manual.rotrics.com/gcode/api-and-sdk)
- [Teach & Play Guide](https://manual.rotrics.com/get-start/picking-and-placing)

## Key Firmware Code Locations

### M_dexarm.cpp - Custom Commands

```
Line ~350: M893 - get_current_encoder()
Line ~360: M894 - process_encoder() 
Line ~370: M895 - get_current_position_from_position_sensor()
Line ~380: M896 - teach_play configuration
Line ~100: M1112 - home command
Line ~200: M1000-M1003 - pneumatic control
```

### Key Functions

| Function | Purpose |
|----------|---------|
| `get_current_encoder()` | Read raw encoder values |
| `get_current_position_from_position_sensor()` | Encoder → Cartesian (forward kinematics) |
| `process_encoder(x,y,z)` | Move to encoder position |
| `set_current_position_from_position_sensor()` | Sync firmware position from encoder |

## URDF - Robot Kinematics

From `DexArm.urdf`:

```
Links:
  B_Fix     - Fixed base
  B_Rot     - Rotating base
  In_1      - Inner arm 1
  In_2      - Inner arm 2  
  Join      - Joint connection
  Out_1     - Outer arm 1 (parallel)
  Out_2     - Outer arm 2 (parallel)
  EE        - End effector

Joint Limits:
  bases (rotation):    -110° to +110°
  B_Rot->In_1:         0° to 90°
  Join->In_2:          -34° to 69°
```

## pydexarm SDK Methods

From `pydexarm.py`:

```python
# Connection
dexarm = Dexarm(port)
dexarm.close()

# Movement
dexarm.go_home()                    # M1112
dexarm.move_to(x, y, z)             # G1 with feedrate
dexarm.fast_move_to(x, y, z)        # G0
dexarm.get_current_position()       # M114 (not M895!)

# Suction Cup (Air Picker)
dexarm.air_picker_pick()            # M1000 - pump in
dexarm.air_picker_place()           # M1001 - pump out (blow)
dexarm.air_picker_nature()          # M1002 - neutral
dexarm.air_picker_stop()            # M1003 - stop

# Soft Gripper (OPPOSITE of suction!)
dexarm.soft_gripper_pick()          # M1001 - pump out to grip
dexarm.soft_gripper_place()         # M1000 - pump in to release
```

## Serial Communication

- Baud: 115200
- Data bits: 8, Stop bits: 1, Parity: None
- Line ending: `\r\n` (CRLF)
- Wait for `ok` after each command

## Useful M-codes Not in pydexarm

| Command | Purpose | Notes |
|---------|---------|-------|
| `M84` | Motors off | Teach mode entry |
| `M17` | Motors on | Lock arm |
| `M893` | Read encoder | Returns M894 format |
| `M894 X Y Z` | Move to encoder | Direct replay |
| `M895` | Encoder → Cartesian | **Use this after M84!** |
| `M400` | Wait for moves | Before reading position |
| `M410` | Quickstop | Can resume |

## Notes From Our Development

### Position Tracking
- `M114` returns last COMMANDED position, not actual
- After teach mode (M84), M114 is WRONG
- Use `M895` to get actual Cartesian from encoders
- Always sync position after exiting teach mode

### Suction Terminology
- "pick" = M1000 (pump IN, creates vacuum)
- "blow/place" = M1001 (pump OUT, releases blade)
- "release" = M1002 (neutral, no pressure)
- "off" = M1003 (stop pump motor)
