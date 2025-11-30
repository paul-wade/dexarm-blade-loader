# DexArm Motion Control

## Coordinate System

```
              +Y (forward)
               ↑
               │
               │
    ───────────┼───────────→ +X (right)
               │
               │
              ARM
             BASE

    +Z = up (away from table)
    -Z = down (toward table)
```

### Home Position

- **X = 0** (center)
- **Y = 300** (extended forward)
- **Z = 0** (reference height)

### Workspace Limits

| Axis | Min | Max | Notes |
|------|-----|-----|-------|
| X | -350 | +350 | Depends on Y |
| Y | 100 | 400 | Can't go behind base |
| Z | -60 | 200 | Module dependent |
| Reach | - | 320 | sqrt(X² + Y²) |

---

## Movement Commands

### G1 - Linear Interpolation (Recommended)

```gcode
G1 [F<feedrate>] [X<pos>] [Y<pos>] [Z<pos>]
```

Moves in a straight line at specified feedrate.

```gcode
G1 F3000 X100 Y250 Z50    ; Full move
G1 Z0                      ; Z only
G1 X50 Y200                ; XY only
```

### G0 - Rapid Movement

```gcode
G0 [F<feedrate>] [X<pos>] [Y<pos>] [Z<pos>]
```

Fastest path (not necessarily straight).

**Control G0 behavior:**
- `M2000` - Make G0 use linear interpolation (like G1)
- `M2001` - Make G0 use rapid movement (default)

---

## Motion Modes

### G90 - Absolute Mode (Default)

Coordinates are absolute positions.

```gcode
G90
G1 X100      ; Move TO X=100
G1 X150      ; Move TO X=150
```

### G91 - Relative Mode

Coordinates are offsets from current position.

```gcode
G91
G1 X10       ; Move +10mm in X
G1 X10       ; Move another +10mm (now at original+20)
G90          ; ALWAYS switch back to absolute!
```

**WARNING**: Always return to G90 after relative moves!

---

## Feedrate

Feedrate is in **mm/min** (not mm/s).

| mm/min | mm/s | Description |
|--------|------|-------------|
| 600 | 10 | Very slow |
| 1200 | 20 | Slow |
| 2000 | 33 | Default |
| 3000 | 50 | Fast |
| 6000 | 100 | Very fast |

```gcode
G1 F3000 X100 Y200 Z50    ; Set feedrate with move
```

Once set, feedrate persists for subsequent moves.

---

## Wait for Movement

### M400 - Wait for Completion

```gcode
G1 X100 Y200 Z50
M400                ; Block until move finishes
M114                ; Now position is accurate
```

**Always use M400 before:**
- Reading position (M114)
- Changing modes
- Any operation that depends on position

---

## Safe Motion Patterns

### Pattern 1: Safe XY Movement

Always lift Z before moving XY to avoid collisions:

```gcode
; Current: X=0, Y=300, Z=10
; Target: X=100, Y=200, Z=10

G1 F3000 Z50         ; 1. Lift to safe height
M400
G1 X100 Y200         ; 2. Move XY
M400
G1 Z10               ; 3. Lower to target
M400
```

### Pattern 2: Pick Operation

```gcode
; Move above pick point
G1 F3000 X100 Y200 Z50
M400

; Start suction BEFORE lowering
M1000
G4 P300              ; Wait 300ms

; Lower to pick
G1 Z0
M400
G4 P500              ; Wait for grab

; Lift with object
G1 Z50
M400
```

### Pattern 3: Place Operation

```gcode
; Already carrying object at Z=50
; Move above place point
G1 F3000 X150 Y250
M400

; Lower to place
G1 Z10
M400

; Release BEFORE lifting
M1002                ; Release pressure
G4 P200
M1003                ; Stop pump

; Lift away
G1 Z50
M400
```

---

## Acceleration

### M204 - Set Acceleration

```gcode
M204                 ; Read current values
M204 P200 T200 R60   ; Set all values
```

| Parameter | Description | Default |
|-----------|-------------|---------|
| P | Printing acceleration | 200 |
| T | Travel acceleration | 200 |
| R | Retract acceleration | 60 |

Higher values = faster but more jerky.

---

## Position Tracking

### M114 - Get Position

```gcode
M400         ; Wait for moves first!
M114
```

Response:
```
X:100.00 Y:200.00 Z:50.00 E:0.00
DEXARM Theta:A:45.00 B:30.00 C:10.00
ok
```

### Position Sync Issues

**Problem**: Software position doesn't match actual position.

**Causes**:
1. Didn't home (M1112) after power on
2. Read position during movement (no M400)
3. Used encoder values (M893) for movement
4. Emergency stop caused position loss

**Fix**:
```gcode
M1112        ; Home resets position
```

---

## Common Mistakes

### ❌ Moving XY at Low Z

```gcode
; At Z=0 near table
G1 X200 Y150         ; DANGER - may hit objects!
```

### ✅ Always Lift First

```gcode
G1 Z50               ; Lift
G1 X200 Y150         ; Safe XY move
G1 Z0                ; Lower
```

### ❌ Reading Position During Move

```gcode
G1 X100 Y200
M114                 ; WRONG - still moving!
```

### ✅ Wait Then Read

```gcode
G1 X100 Y200
M400                 ; Wait
M114                 ; Accurate
```
