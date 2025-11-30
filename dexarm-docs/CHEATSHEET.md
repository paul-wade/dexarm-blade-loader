# DexArm Quick Reference Cheat Sheet

Print this! Keep it next to your arm!

---

## Startup Sequence

```gcode
; 1. Connect (115200 baud)
; 2. Send these commands:
M1112        ; HOME - ALWAYS FIRST!
M888 P2      ; Set module (P2 = pneumatic)
```

---

## Movement

| Command | Action |
|---------|--------|
| `G1 F3000 X100 Y200 Z50` | Move to position |
| `G1 Z50` | Move Z only |
| `G1 X100 Y200` | Move XY only |
| `M400` | Wait for move |
| `M114` | Get position |

**Safe pattern:**
```gcode
G1 Z50          ; 1. Lift
G1 X100 Y200    ; 2. Move XY
G1 Z0           ; 3. Lower
```

---

## Suction Cup

| Command | Action |
|---------|--------|
| `M1000` | Suction ON (pick) |
| `M1001` | Blow OUT |
| `M1002` | Release pressure |
| `M1003` | Stop pump |

**Pick pattern:**
```gcode
M1000           ; Suction ON
G4 P300         ; Wait 300ms
G1 Z0           ; Lower
G4 P500         ; Grab delay
G1 Z50          ; Lift
```

**Place pattern:**
```gcode
G1 Z10          ; Lower
M1002           ; Release
G4 P200         ; Wait
M1003           ; Stop
G1 Z50          ; Lift
```

---

## Teach Mode

| Command | Action |
|---------|--------|
| `M84` | Motors OFF (free move) |
| `M17` | Motors ON (lock) |
| `M893` | Read encoder position |
| `M894 X... Y... Z...` | Move to encoder pos |

---

## Stop Commands

| Command | Action | Recovery |
|---------|--------|----------|
| `M410` | Quickstop | G1 to continue |
| `M112` | EMERGENCY | Reboot! |
| `M2007` | Reboot arm | Wait 5s |

---

## Modules

| Command | Module |
|---------|--------|
| `M888 P0` | Pen |
| `M888 P1` | Laser |
| `M888 P2` | Pneumatic |
| `M888 P3` | 3D Print |

---

## ⚠️ Don't Confuse!

| Wrong | Right | Why |
|-------|-------|-----|
| M112 | M1112 | M112 = emergency stop! |
| Moving at low Z | Lift first | Avoid crashes |
| M114 during move | M400 then M114 | Position wrong |

---

## Coordinate System

```
Home = (X:0, Y:300, Z:0)

         +Y (forward)
          ↑
          │
    ──────┼──────→ +X (right)
          │
         BASE
```

---

## Feedrate Reference

| mm/min | mm/s | Use |
|--------|------|-----|
| 1000 | 17 | Slow/precise |
| 2000 | 33 | Default |
| 3000 | 50 | Fast |

---

## Serial Settings

- **Baud**: 115200
- **Bits**: 8N1
- **Line ending**: CR+LF (`\r\n`)
- **Wait for**: `ok` response
