# Common Errors & Fixes

## Critical Mistakes We Made

### ❌ Mistake 1: M112 vs M1112

**Wrong:**
```gcode
M112    ; THIS IS EMERGENCY STOP - ARM FREEZES!
```

**Right:**
```gcode
M1112   ; This is HOME command
```

**Recovery**: If you sent M112, power cycle the arm or send `M2007` to reboot.

---

### ❌ Mistake 2: Using Encoder Values as Coordinates

**Wrong:**
```python
# DON'T DO THIS!
encoder = read_m893()  # Returns "M894 X1234 Y5678 Z9012"
# These are NOT millimeters! They're raw encoder ticks!
```

**Right:**
```python
# Use M893/M894 ONLY for teach & play
# For movement, always use Cartesian G1 commands:
send("G1 F2000 X100 Y250 Z50")

# If you need teach & play:
send("M84")           # Free move mode
# User positions arm
send("M17")           # Lock
encoder = read_m893() # Save this exact string
# Later replay with that exact string
```

---

### ❌ Mistake 3: Reading Position During Movement

**Wrong:**
```python
send("G1 X100 Y200 Z50")
position = read_m114()  # WRONG - arm is still moving!
```

**Right:**
```python
send("G1 X100 Y200 Z50")
send("M400")            # Wait for move to complete
position = read_m114()  # Now it's accurate
```

---

### ❌ Mistake 4: Forgetting to Wait for OK

**Wrong:**
```python
serial.write(b"G1 X100\r\n")
serial.write(b"G1 X200\r\n")  # May be ignored!
serial.write(b"G1 X300\r\n")  # Buffer overflow!
```

**Right:**
```python
send_and_wait("G1 X100")  # Wait for "ok"
send_and_wait("G1 X200")  # Wait for "ok"
send_and_wait("G1 X300")  # Wait for "ok"
```

---

### ❌ Mistake 5: Not Setting Module Type

**Wrong:**
```python
connect()
send("M1000")  # Suction may not work - wrong offset!
```

**Right:**
```python
connect()
send("M1112")     # Home first
send("M888 P2")   # Set pneumatic module
send("M1000")     # Now suction works correctly
```

---

### ❌ Mistake 6: Moving XY at Low Z

**Wrong:**
```python
# Arm is at Z=-20 (close to table)
send("G1 X200 Y150")  # CRASH! May hit objects
```

**Right:**
```python
# Always lift first, then move XY, then lower
send("G1 Z50")              # Lift to safe height
send("G1 X200 Y150")        # Move XY
send("G1 Z-20")             # Lower to target
```

---

### ❌ Mistake 7: Not Homing After Power On

**Wrong:**
```python
connect()
send("G1 X100 Y200 Z50")  # Arm doesn't know where it is!
```

**Right:**
```python
connect()
send("M1112")             # ALWAYS home first
send("G1 X100 Y200 Z50")  # Now movement is accurate
```

---

### ❌ Mistake 8: Suction vs Soft Gripper Commands

**Suction Cup:**
```gcode
M1000   ; Pump IN = PICK (creates vacuum)
M1001   ; Pump OUT = RELEASE (blows air)
```

**Soft Gripper (OPPOSITE!):**
```gcode
M1001   ; Pump OUT = GRIP (closes fingers)
M1000   ; Pump IN = RELEASE (opens fingers)
```

---

## Error Messages

| Message | Cause | Fix |
|---------|-------|-----|
| `unknown command` | Typo or unsupported command | Check spelling |
| `MINTEMP` | 3D print head too cold | Heat up or ignore if not printing |
| `MAXTEMP` | 3D print head too hot | Cool down, check thermistor |
| `Endstop hit` | Arm reached limit | Move away from limit |
| No response | Port wrong or arm off | Check connection |

---

## Recovery Procedures

### Arm Frozen (After M112)

```python
# Option 1: Software reboot
send("M2007")
time.sleep(5)
send("M1112")  # Re-home

# Option 2: Power cycle
# Turn off, wait 5 seconds, turn on
# Then reconnect and home
```

### Arm in Unknown Position

```python
# 1. Enable teach mode
send("M84")

# 2. Manually move arm to a safe position

# 3. Re-enable and home
send("M17")
send("M1112")
```

### Position Drifted / Inaccurate

```python
# 1. Go home to reset position
send("M1112")

# 2. If still wrong, recalibrate:
# a. Move arm to calibration position (see manual)
# b. Send M889
# c. Home again with M1112
```

---

## Safe Coding Patterns

### Always Use This Pattern

```python
class DexArm:
    def __init__(self, port):
        self.ser = serial.Serial(port, 115200, timeout=2)
        time.sleep(2)
        self.home()
    
    def send(self, cmd):
        self.ser.write(f"{cmd}\r\n".encode())
        while True:
            line = self.ser.readline().decode().strip()
            if "ok" in line.lower():
                return
    
    def home(self):
        self.send("M1112")
        time.sleep(2)
    
    def move_safe(self, x, y, z, safe_z=50):
        """Always lift before XY movement."""
        self.send(f"G1 F3000 Z{safe_z}")  # Lift
        self.send("M400")
        self.send(f"G1 X{x} Y{y}")        # Move XY
        self.send("M400")
        self.send(f"G1 Z{z}")             # Lower
        self.send("M400")
    
    def pick(self):
        self.send("M1000")  # Suction on
        time.sleep(0.5)     # Wait for vacuum
    
    def place(self):
        self.send("M1002")  # Release pressure
        time.sleep(0.3)
        self.send("M1003")  # Stop pump
```
