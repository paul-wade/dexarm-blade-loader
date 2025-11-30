# DexArm Serial Communication Protocol

## Connection Parameters

| Setting | Value |
|---------|-------|
| Baud Rate | 115200 |
| Data Bits | 8 |
| Stop Bits | 1 |
| Parity | None |
| Flow Control | None |
| Line Ending | CR+LF (`\r\n` or `0D0A`) |

## Protocol

### Request/Response Pattern

DexArm uses a simple command-response protocol:

1. Host sends command ending with `\r\n`
2. Arm executes command
3. Arm responds with `ok` (or error message)
4. Host can send next command

```python
# Correct pattern
serial.write(b"G1 X100 Y200 Z50\r\n")
response = serial.readline()  # Wait for "ok"
```

### Response Types

| Response | Meaning |
|----------|---------|
| `ok` | Command executed successfully |
| `unknown command` | Command not recognized |
| `error:...` | Error occurred |
| Data line | Query response (before `ok`) |

### Example M114 Response

```
X:100.00 Y:250.00 Z:50.00 E:0.00
DEXARM Theta:A:45.00 B:30.00 C:10.00
ok
```

### Example M893 Response

```
M894 X1234 Y5678 Z9012
ok
```

## Timing Considerations

### Wait for OK

Always wait for `ok` before sending the next command:

```python
def send_command(serial, cmd):
    serial.write(f"{cmd}\r\n".encode())
    while True:
        response = serial.readline().decode().strip()
        if "ok" in response.lower():
            return response
```

### Buffer Overflow

If you send commands without waiting for `ok`, the arm's buffer may overflow and commands will be ignored.

**Exception**: Use `wait=False` only for fire-and-forget commands like emergency stop:

```python
def emergency_stop(serial):
    serial.write(b"M410\r\n")
    serial.reset_input_buffer()  # Don't wait
```

### Connection Startup

After opening serial port, wait 2 seconds before sending commands:

```python
serial = Serial(port, 115200, timeout=2)
time.sleep(2)  # Wait for DexArm to initialize
serial.write(b"M1112\r\n")  # Now send home command
```

## Python Implementation

### Minimal Working Example

```python
import serial
import time

def connect(port):
    ser = serial.Serial(port, 115200, timeout=2)
    time.sleep(2)
    return ser

def send(ser, cmd):
    ser.write(f"{cmd}\r\n".encode())
    while True:
        line = ser.readline().decode().strip()
        if "ok" in line.lower():
            return
        if line:
            print(f"  Response: {line}")

def main():
    ser = connect("COM3")
    
    send(ser, "M1112")          # Home
    send(ser, "M888 P2")        # Pneumatic module
    send(ser, "G1 F2000 X0 Y250 Z50")
    send(ser, "M400")           # Wait for move
    send(ser, "M1000")          # Suction on
    
    ser.close()

if __name__ == "__main__":
    main()
```

### Reading Position

```python
import re

def get_position(ser):
    ser.reset_input_buffer()
    ser.write(b"M114\r\n")
    
    x, y, z = None, None, None
    while True:
        line = ser.readline().decode().strip()
        if "X:" in line:
            # Parse "X:100.00 Y:200.00 Z:50.00 E:0.00"
            match = re.findall(r"[-+]?\d*\.?\d+", line)
            if len(match) >= 3:
                x, y, z = float(match[0]), float(match[1]), float(match[2])
        if "ok" in line.lower():
            return x, y, z
```

## Common Issues

### Issue: Commands Ignored

**Cause**: Not waiting for `ok` response.

**Fix**: Always wait for `ok` before sending next command.

### Issue: Position Reads Wrong Values

**Cause**: Reading position while arm is moving.

**Fix**: Send `M400` before `M114`:

```python
send(ser, "M400")    # Wait for moves to finish
x, y, z = get_position(ser)
```

### Issue: Serial Port Won't Open

**Cause**: Another application has the port open.

**Fix**: Close Rotrics Studio or other software using the port.

### Issue: No Response from Arm

**Cause**: Wrong port, wrong baud rate, or arm not powered.

**Fix**: Check port in Device Manager, verify 115200 baud, check power.
