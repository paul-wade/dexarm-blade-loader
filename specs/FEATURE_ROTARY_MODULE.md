# Feature: Rotary Module Support

## Goal

Use the DexArm rotary module (4th axis) to rotate blades so the slot aligns with hooks.

## Current State

- No rotary support
- Blades must be manually oriented in stack
- Hope slot lines up with hook

## Target State

- Detect if rotary module is attached
- Rotate blade after pick to align slot with hook
- Each stack/hook can specify orientation angle
- Teach rotation angle just like XYZ positions

## Hardware Commands

```gcode
M888 P6         ; Initialize rotary module
M2100           ; Initialize rotary
M2101           ; Read current angle (returns "Angle: n")
M2101 Pn        ; Go to absolute angle (0-360°)
M2101 Rn        ; Rotate relative (+ = clockwise, - = counter)
M2101 Sn        ; Continuous rotation (speed 0-100, negative = reverse)
M2103           ; Check firmware version
```

### Examples

```gcode
M2101           ; → "Angle: 45" (read current)
M2101 P90       ; Go to 90°
M2101 R-30      ; Rotate 30° counter-clockwise
M2101 S50       ; Spin clockwise at speed 50
M2101 S0        ; Stop spinning
```

## Data Model Changes

```python
@dataclass
class PickStack:
    # ... existing fields ...
    orientation_deg: float = 0   # Blade slot direction in stack

@dataclass  
class Hook:
    # ... existing fields ...
    orientation_deg: float = 90  # Direction hook faces
```

## Implementation

```python
class RotaryControl:
    def init_module(self):
        """Initialize rotary module."""
        self.send("M888 P6")
        self.send("M2100")
    
    def read_angle(self) -> float:
        """Read current rotation angle."""
        response = self.send("M2101")
        # Parse "Angle: 45.0" from response
        match = re.search(r'Angle:\s*([\d.]+)', response)
        return float(match.group(1)) if match else 0.0
    
    def rotate_to(self, degrees: float):
        """Rotate to absolute angle (0-360)."""
        self.send(f"M2101 P{degrees}")
        self.send("M400")
    
    def rotate_relative(self, degrees: float):
        """Rotate relative to current position."""
        self.send(f"M2101 R{degrees}")
        self.send("M400")
```

## Teach Mode for Rotation

Just like XYZ teach mode:

```python
def teach_rotation(self) -> float:
    """Read current angle for saving."""
    # User manually rotates module to desired position
    # Then we read and save it
    return self.read_angle()

def save_hook_with_rotation(self, hook_position: Position, rotation: float):
    """Save hook with its rotation angle."""
    return Hook(
        position=hook_position,
        orientation_deg=rotation,
        stack_name="main"
    )
```

## Pick-Place Sequence

```python
def place_blade_with_rotation(stack: PickStack, hook: Hook):
    # Pick (blade at stack orientation)
    pick_blade(stack.position)
    
    # Calculate rotation needed
    rotation = hook.orientation_deg - stack.orientation_deg
    
    # Rotate blade to align with hook
    rotary.rotate_to(rotation)
    
    # Place
    place_blade(hook.position)
    
    # Return to neutral for next pick
    rotary.rotate_to(0)
```

## Detection

```python
def has_rotary_module() -> bool:
    """Check if rotary module is connected."""
    # Option 1: Try M888 P3, check response
    # Option 2: Config flag
    # Option 3: Query firmware
    pass
```

## UI Changes

```
┌─────────────────────────────────────┐
│  ROTARY MODULE                      │
├─────────────────────────────────────┤
│  Status: [Connected / Not Found]    │
│  Current Angle: 45°                 │
│  [Home Rotation] [Go to 0°]         │
└─────────────────────────────────────┘

Stack orientation:  [0°  ▼]  (slot faces +Y)
Hook orientation:   [90° ▼]  (hook faces +X)
```

## Tasks

- [ ] Research rotary module G-codes (M888 P3, G28 E, etc.)
- [ ] Add `RotaryControl` class
- [ ] Add orientation fields to Stack and Hook
- [ ] Detect rotary module presence
- [ ] Integrate rotation into place sequence
- [ ] UI for orientation settings
- [ ] Test rotation angles

## Open Questions

1. Can user manually rotate the module by hand when motors off?
2. Does M2101 work during teach mode (M84)?
3. Speed limits for rotation with blade attached?

## Success Criteria

- [ ] Rotary module detected automatically
- [ ] Can read current angle with M2101
- [ ] Can teach rotation like XYZ (manual rotate → read → save)
- [ ] Blade rotates to align with hook during place
- [ ] Rotation angle saved per hook in JSON
