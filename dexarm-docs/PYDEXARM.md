# Official pydexarm API Reference

The official Python API from Rotrics. This is the reference implementation.

**Source**: https://github.com/Rotrics-Dev/DexArm_API/blob/master/pydexarm/pydexarm.py

---

## Installation

```bash
pip install pyserial
```

Then copy `pydexarm.py` from the official repo.

---

## Class: Dexarm

### Constructor

```python
from pydexarm import Dexarm

arm = Dexarm("COM3")  # Windows
arm = Dexarm("/dev/ttyUSB0")  # Linux
```

### Core Methods

#### `go_home()`

Move to home position (X=0, Y=300, Z=0). **Always call first!**

```python
arm.go_home()
```

G-code: `M1112`

---

#### `move_to(x, y, z, e=None, feedrate=2000, mode="G1", wait=True)`

Move to Cartesian position.

```python
arm.move_to(x=100, y=250, z=50)
arm.move_to(x=100, y=250, z=50, feedrate=3000)
arm.move_to(x=100, y=250, z=50, mode="G0")  # Fast mode
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| x | float | None | X position in mm |
| y | float | None | Y position in mm |
| z | float | None | Z position in mm |
| e | float | None | Extruder position |
| feedrate | int | 2000 | Speed in mm/min |
| mode | str | "G1" | "G0" or "G1" |
| wait | bool | True | Wait for completion |

---

#### `get_current_position()`

Get current position.

```python
x, y, z, e, a, b, c = arm.get_current_position()
print(f"Position: X={x}, Y={y}, Z={z}")
```

Returns: `(x, y, z, e, a, b, c)` - Cartesian + theta angles

G-code: `M114`

---

#### `set_module_type(module_type)`

Set front-end module type.

```python
arm.set_module_type(0)  # Pen
arm.set_module_type(1)  # Laser
arm.set_module_type(2)  # Pneumatic
arm.set_module_type(3)  # 3D printing
```

G-code: `M888 P{n}`

---

#### `get_module_type()`

Get current module type.

```python
module = arm.get_module_type()  # Returns 'PEN', 'LASER', 'PUMP', or '3D'
```

---

### Pneumatic Methods

#### Suction Cup (Air Picker)

```python
arm.air_picker_pick()     # M1000 - Pump IN (grab)
arm.air_picker_place()    # M1001 - Pump OUT (release)
arm.air_picker_nature()   # M1002 - Neutral
arm.air_picker_stop()     # M1003 - Stop
```

#### Soft Gripper (OPPOSITE commands!)

```python
arm.soft_gripper_pick()   # M1001 - Pump OUT (grip)
arm.soft_gripper_place()  # M1000 - Pump IN (release)
arm.soft_gripper_nature() # M1002 - Neutral
arm.soft_gripper_stop()   # M1003 - Stop
```

---

### Laser Methods

```python
arm.laser_on(power=100)   # M3 S100 (power 0-255)
arm.laser_off()           # M5
```

---

### Timing Methods

```python
arm.dealy_ms(500)  # G4 P500 - Wait 500ms (note: typo in original)
arm.dealy_s(2)     # G4 S2 - Wait 2 seconds
```

---

### Conveyor Belt Methods

```python
arm.conveyor_belt_forward(speed=1000)   # M2012 F1000 D0
arm.conveyor_belt_backward(speed=1000)  # M2012 F1000 D1
arm.conveyor_belt_stop()                # M2013
```

---

### Sliding Rail Methods

```python
arm.sliding_rail_init()  # M2005 - Home the rail
```

---

### Other Methods

```python
arm.set_workorigin()              # G92 X0 Y0 Z0 E0
arm.set_acceleration(200, 200)    # M204 P200 T200
arm.close()                       # Close serial port
```

---

## Example: Pick and Place

```python
from pydexarm import Dexarm
import time

arm = Dexarm("COM3")
arm.go_home()
arm.set_module_type(2)  # Pneumatic

# Pick position
arm.move_to(x=100, y=200, z=50)  # Above pick
arm.air_picker_pick()            # Start suction
arm.move_to(z=0)                 # Lower to pick
time.sleep(0.5)                  # Wait for vacuum
arm.move_to(z=50)                # Lift

# Place position
arm.move_to(x=150, y=250, z=50)  # Above place
arm.move_to(z=10)                # Lower to place
arm.air_picker_place()           # Release
time.sleep(0.3)
arm.air_picker_stop()
arm.move_to(z=50)                # Lift away

arm.go_home()
arm.close()
```

---

## Internal Method: `_send_cmd`

```python
def _send_cmd(self, data, wait=True):
    """
    Send command to the arm.
    
    Args:
        data: Command string (without \r\n - added automatically)
        wait: If True, block until 'ok' received
              If False, don't wait (buffer may overflow!)
    """
```

**Note**: The `\r` is added by the method. Commands are sent with `\r` (CR only), but the arm also accepts `\r\n`.
