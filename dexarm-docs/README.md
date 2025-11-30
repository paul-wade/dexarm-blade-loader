# DexArm Complete Documentation

> ⚠️ **IMPORTANT**: DexArm uses **CUSTOM Marlin firmware**, NOT standard Marlin!
> Many commands (M1112, M893, M1000, etc.) are DexArm-specific.

**Official resources verified and compiled from:**

- [Rotrics Manual](https://manual.rotrics.com/gcode/api-and-sdk)
- [Official Python API](https://github.com/Rotrics-Dev/DexArm_API)
- [Custom Marlin Firmware](https://github.com/Rotrics-Dev/Marlin_For_DexArm) ← **DexArm_Dev branch**

---

## Quick Reference

| Action | Command | Notes |
|--------|---------|-------|
| Home | `M1112` | **Always call first!** Moves to X0 Y300 Z0 |
| Move | `G1 F2000 X100 Y250 Z50` | Linear move with feedrate |
| Wait | `M400` | Wait for moves to complete |
| Get position | `M114` | Returns commanded position |
| **Actual position** | `M895` | ⚠️ **Use after teach mode!** |
| Set module | `M888 P2` | P2 = pneumatic/suction |
| Suction ON | `M1000` | Pump IN (pick object) |
| Blow/Place | `M1001` | Pump OUT (release object) |
| Neutral | `M1002` | Release air pressure |
| Pump OFF | `M1003` | Stop pump motor |
| E-Stop | `M410` | Quickstop (can resume) |
| Motors off | `M84` | Free move / teach mode |
| Motors on | `M17` | Lock arm |

---

## Document Index

1. **[FIRMWARE.md](./FIRMWARE.md)** - ⚠️ Custom Marlin - READ FIRST!
2. **[COMMANDS.md](./COMMANDS.md)** - Complete G-code reference
3. **[TEACH_MODE.md](./TEACH_MODE.md)** - 🎓 Teach & play, position syncing
4. **[COMMUNICATION.md](./COMMUNICATION.md)** - Serial protocol details
5. **[MOTION.md](./MOTION.md)** - Motion control & modes
6. **[ERRORS.md](./ERRORS.md)** - Common mistakes & fixes
7. **[PYDEXARM.md](./PYDEXARM.md)** - Official Python API reference
8. **[RESOURCES.md](./RESOURCES.md)** - 🔗 Official repos & code locations
9. **[CHEATSHEET.md](./CHEATSHEET.md)** - Printable quick reference

---

## Critical Notes

### ⚠️ Common Mistakes We Made

1. **M1112 vs M112** - `M1112` = Home, `M112` = EMERGENCY STOP (requires reboot!)
2. **Encoder values (M893/M894)** - These are NOT Cartesian coordinates! Don't use for general movement
3. **Feedrate units** - DexArm uses mm/min, not mm/s (F2000 = 33mm/s)
4. **Y-axis center** - Home is Y=300, not Y=0. Y range is ~100-400mm
5. **Wait for moves** - Always send `M400` before reading position

### Coordinate System

```
        +Y (forward, toward front)
         ↑
         │
         │
  ───────┼───────→ +X (right)
         │
         │
        ARM BASE

+Z = up (away from table)
-Z = down (toward table)

Home position: X=0, Y=300, Z=0
```

### Workspace Limits

| Axis | Min | Max | Notes |
|------|-----|-----|-------|
| X | -350 | +350 | At Y=300 |
| Y | 100 | 400 | Can't go behind base |
| Z | -60 | 200 | Module dependent |
| Reach | - | 320 | sqrt(X² + Y²) |
