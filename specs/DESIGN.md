# Blade Loader v2 - Spec-First Design

## Problem Statement

Build a reliable pick-and-place system for loading razor blades onto coating racks using a DexArm robot arm. Previous attempts failed due to:

1. **Inconsistent motion patterns** - No clear contract for when to use safe vs direct moves
2. **Position state drift** - Software position tracking diverges from actual arm
3. **No testability** - Can't verify correctness without physical hardware
4. **Mixed abstractions** - Raw G-code mixed with high-level operations

---

## Design Goals

1. **Predictable**: Same input → same motion sequence, every time
2. **Testable**: Property-based tests verify invariants without hardware
3. **Recoverable**: Can detect and recover from position drift
4. **Auditable**: Full trace of every command sent

---

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                         │
│  - GUI / API endpoints                                       │
│  - User workflows (teach, run cycle)                         │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│                   Orchestration Layer                        │
│  - MotionPlanner: Converts goals → motion sequences          │
│  - WorkflowEngine: State machine for pick-place cycles       │
│  - PositionManager: Single source of truth for position      │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│                    Command Layer                             │
│  - CommandQueue: Ordered, auditable command buffer           │
│  - CommandExecutor: Send commands, wait for ACK              │
│  - GCodeBuilder: Type-safe G-code construction               │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│                   Transport Layer                            │
│  - SerialTransport: Bytes over serial port                   │
│  - MockTransport: For testing without hardware               │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Invariants (Property-Based Test Targets)

### Motion Invariants

```python
# INV-1: Safe moves always lift Z first
def safe_move_lifts_first(commands: List[Command]) -> bool:
    """A safe move sequence must begin with Z-up before any XY motion."""
    for seq in extract_safe_move_sequences(commands):
        first_with_xy = find_first_xy_change(seq)
        first_with_z = find_first_z_change(seq)
        if first_with_xy and first_with_z:
            assert first_with_z.index < first_with_xy.index
            assert first_with_z.direction == "up"

# INV-2: No XY motion below safe_z when carrying blade
def no_low_xy_with_blade(state: ArmState, commands: List[Command]) -> bool:
    """While carrying a blade, never move XY if Z < safe_z."""
    if state.carrying_blade:
        for cmd in commands:
            if cmd.changes_xy() and state.z < state.safe_z:
                return False
    return True

# INV-3: Position tracking matches actual (within tolerance)
def position_in_sync(tracked: Position, actual: Position) -> bool:
    """Tracked position should match actual within 0.1mm."""
    return (
        abs(tracked.x - actual.x) < 0.1 and
        abs(tracked.y - actual.y) < 0.1 and
        abs(tracked.z - actual.z) < 0.1
    )

# INV-4: Commands are idempotent-safe
def commands_complete_before_next(commands: List[Command]) -> bool:
    """Every move command is followed by M400 (wait) before the next move."""
    for i, cmd in enumerate(commands[:-1]):
        if cmd.is_move():
            next_cmd = commands[i + 1]
            assert next_cmd.is_wait() or not commands[i + 1].is_move()
```

### State Machine Invariants

```python
# INV-5: States transition in valid order
def valid_state_transitions(history: List[State]) -> bool:
    """State transitions must follow the defined graph."""
    valid_transitions = {
        "IDLE": ["LIFTING_TO_SAFE"],
        "LIFTING_TO_SAFE": ["MOVING_XY_ABOVE_PICK"],
        "MOVING_XY_ABOVE_PICK": ["LOWERING_TO_PICK"],
        # ... etc
    }
    for i, state in enumerate(history[:-1]):
        next_state = history[i + 1]
        assert next_state.name in valid_transitions[state.name]

# INV-6: Suction state matches blade state
def suction_blade_consistency(state: ArmState) -> bool:
    """If carrying blade, suction must be ON. If not carrying, suction OFF."""
    if state.carrying_blade:
        assert state.suction == SuctionState.ON
    # Note: suction can be ON briefly before grabbing (pre-activation)
```

### Recovery Invariants

```python
# INV-7: After error, arm is in safe state
def safe_after_error(pre_error: ArmState, post_recovery: ArmState) -> bool:
    """After any error recovery, Z must be at safe height."""
    return post_recovery.z >= post_recovery.safe_z

# INV-8: Position is re-synced after error
def position_synced_after_error(arm: Arm) -> bool:
    """After error recovery, tracked position must match encoder."""
    actual = arm.read_encoder_position()
    return position_in_sync(arm.tracked_position, actual)
```

---

## Motion Policy Specification

### Policy: SAFE (Default for carrying blade)

```
Input: target(x, y, z), current(cx, cy, cz), safe_z
Output: Command sequence

1. IF cz < safe_z: EMIT G1 Z{safe_z} + M400
2. IF cx != x OR cy != y: EMIT G1 X{x} Y{y} + M400
3. IF z != safe_z: EMIT G1 Z{z} + M400
```

### Policy: DIRECT (Only when not carrying blade)

```
Input: target(x, y, z), current(cx, cy, cz)
Output: Command sequence

1. EMIT G1 X{x} Y{y} Z{z} + M400
```

### Policy: Z_ONLY

```
Input: target_z, current_z
Output: Command sequence

1. EMIT G1 Z{target_z} + M400
```

---

## Command Types (Strongly Typed)

```python
@dataclass(frozen=True)
class MoveCommand:
    """Immutable move command."""
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    feedrate: int = 3000
    
    def to_gcode(self) -> str:
        parts = ["G1", f"F{self.feedrate}"]
        if self.x is not None: parts.append(f"X{self.x:.2f}")
        if self.y is not None: parts.append(f"Y{self.y:.2f}")
        if self.z is not None: parts.append(f"Z{self.z:.2f}")
        return " ".join(parts)
    
    def changes_xy(self) -> bool:
        return self.x is not None or self.y is not None
    
    def changes_z(self) -> bool:
        return self.z is not None

@dataclass(frozen=True)
class WaitCommand:
    """Wait for moves to complete."""
    def to_gcode(self) -> str:
        return "M400"

@dataclass(frozen=True)  
class SuctionCommand:
    """Suction control."""
    action: Literal["on", "release", "off"]
    
    def to_gcode(self) -> str:
        return {"on": "M1000", "release": "M1002", "off": "M1003"}[self.action]

Command = Union[MoveCommand, WaitCommand, SuctionCommand, HomeCommand, ...]
```

---

## MotionPlanner API

```python
class MotionPlanner:
    """Plans motion sequences that satisfy invariants."""
    
    def __init__(self, position_manager: PositionManager, safe_z: float):
        self.pos = position_manager
        self.safe_z = safe_z
    
    def plan_safe_move(self, target: Position) -> List[Command]:
        """Plan a safe move (Z-up, XY, Z-down)."""
        commands = []
        current = self.pos.current
        
        # 1. Lift to safe Z if needed
        if current.z < self.safe_z:
            commands.append(MoveCommand(z=self.safe_z))
            commands.append(WaitCommand())
        
        # 2. Move XY if needed
        if current.x != target.x or current.y != target.y:
            commands.append(MoveCommand(x=target.x, y=target.y))
            commands.append(WaitCommand())
        
        # 3. Lower to target Z if needed
        if target.z != self.safe_z:
            commands.append(MoveCommand(z=target.z))
            commands.append(WaitCommand())
        
        return commands
    
    def plan_pick_sequence(self, pick_pos: Position) -> List[Command]:
        """Plan complete pick sequence."""
        commands = []
        
        # Move safely above pick
        commands.extend(self.plan_safe_move(Position(pick_pos.x, pick_pos.y, self.safe_z)))
        
        # Turn on suction BEFORE lowering
        commands.append(SuctionCommand("on"))
        commands.append(DelayCommand(0.3))
        
        # Lower to pick
        commands.append(MoveCommand(z=pick_pos.z))
        commands.append(WaitCommand())
        
        # Wait for grab
        commands.append(DelayCommand(0.5))
        
        # Lift with blade
        commands.append(MoveCommand(z=self.safe_z))
        commands.append(WaitCommand())
        
        return commands
```

---

## Testing Strategy

### Layer 1: Unit Tests (Pure Functions)

```python
# Test GCodeBuilder output
def test_move_command_format():
    cmd = MoveCommand(x=100.5, y=200.0, z=50.0, feedrate=3000)
    assert cmd.to_gcode() == "G1 F3000 X100.50 Y200.00 Z50.00"

def test_move_z_only():
    cmd = MoveCommand(z=50.0, feedrate=2000)
    assert cmd.to_gcode() == "G1 F2000 Z50.00"
    assert cmd.changes_z() == True
    assert cmd.changes_xy() == False
```

### Layer 2: Property-Based Tests (Invariants)

```python
from hypothesis import given, strategies as st

@given(
    current=st.builds(Position, st.floats(-100, 100), st.floats(100, 400), st.floats(-50, 200)),
    target=st.builds(Position, st.floats(-100, 100), st.floats(100, 400), st.floats(-50, 200)),
    safe_z=st.floats(0, 100)
)
def test_safe_move_lifts_first(current, target, safe_z):
    planner = MotionPlanner(MockPositionManager(current), safe_z)
    commands = planner.plan_safe_move(target)
    
    # Find first command that changes XY
    first_xy = next((i for i, c in enumerate(commands) if c.changes_xy()), None)
    first_z_up = next((i for i, c in enumerate(commands) 
                       if c.changes_z() and c.z >= safe_z), None)
    
    # If there's XY movement and we were below safe_z, must lift first
    if first_xy is not None and current.z < safe_z:
        assert first_z_up is not None
        assert first_z_up < first_xy
```

### Layer 3: Simulation Tests (State Machine)

```python
def test_full_cycle_state_transitions():
    """Run full cycle with mock transport, verify state sequence."""
    transport = MockTransport()
    arm = ArmController(transport)
    
    # Run cycle
    cycle = PickPlaceCycle(arm, positions)
    cycle.run()
    
    # Verify state sequence
    assert cycle.state_history == [
        "IDLE",
        "LIFTING_TO_SAFE",
        "MOVING_XY_ABOVE_PICK",
        "LOWERING_TO_PICK",
        "GRABBING",
        "LIFTING_WITH_BLADE",
        "MOVING_XY_ABOVE_HOOK",
        "LOWERING_TO_HOOK",
        "RELEASING",
        "LIFTING_FROM_HOOK",
        "HOMING",
        "IDLE"
    ]
    
    # Verify all motion invariants held
    assert all_safe_moves_lifted_first(transport.command_log)
```

### Layer 4: Integration Tests (With Hardware or HIL Simulator)

```python
@pytest.mark.hardware
def test_position_sync_after_moves():
    """Verify tracked position matches encoder after sequence."""
    arm = ArmController(RealSerialTransport("COM3"))
    arm.home()
    
    # Move to various positions
    arm.move_safe(100, 200, 50)
    arm.move_safe(150, 250, 30)
    
    # Check position sync
    tracked = arm.position
    actual = arm.read_encoder_position()
    
    assert abs(tracked.x - actual.x) < 0.5
    assert abs(tracked.y - actual.y) < 0.5
    assert abs(tracked.z - actual.z) < 0.5
```

---

## Frameworks to Evaluate

### Motion/Robotics

| Framework | Pros | Cons | Use Case |
|-----------|------|------|----------|
| **python-statemachine** | Simple, visual | Limited | State machine |
| **transitions** | Full-featured FSM | Complexity | Complex workflows |
| **ROS2 (micro-ROS)** | Industry standard | Heavy | Overkill for this |
| **Custom** | Tailored | More work | Best fit |

### Testing

| Framework | Pros | Cons | Use Case |
|-----------|------|------|----------|
| **Hypothesis** | Best PBT for Python | Learning curve | Property tests |
| **pytest** | Standard | Basic | Unit tests |
| **pytest-bdd** | Readable specs | Verbose | Behavior specs |

### Recommendation

- **State Machine**: `transitions` library (mature, well-documented)
- **PBT**: `hypothesis` (gold standard for Python)
- **Testing**: `pytest` + `hypothesis`
- **Architecture**: Custom layers following SOLID (started in v1)

---

## Implementation Plan

### Phase 1: Core Types & Invariants (Day 1)
- [ ] Define `Position`, `Command` types (immutable, typed)
- [ ] Define all invariants as hypothesis tests
- [ ] Implement `GCodeBuilder` with tests

### Phase 2: Motion Planner (Day 2)
- [ ] Implement `MotionPlanner` with policy-based planning
- [ ] PBT: All plans satisfy motion invariants
- [ ] Unit tests for each motion policy

### Phase 3: Command Execution (Day 3)
- [ ] Implement `CommandExecutor` with audit log
- [ ] Implement `MockTransport` for testing
- [ ] Integration tests with mock

### Phase 4: State Machine (Day 4)
- [ ] Implement states using `transitions` library
- [ ] PBT: State transitions are valid
- [ ] Full cycle simulation test

### Phase 5: Position Management (Day 5)
- [ ] Implement `PositionManager` (single source of truth)
- [ ] Position sync/recovery logic
- [ ] PBT: Position invariants hold

### Phase 6: API & UI (Day 6-7)
- [ ] FastAPI endpoints (reuse existing patterns)
- [ ] React UI (reuse existing with fixes)
- [ ] End-to-end tests

---

## File Structure

```
blade-loader-v2/
├── src/
│   ├── core/
│   │   ├── types.py          # Position, Command types
│   │   ├── gcode.py          # GCodeBuilder
│   │   └── invariants.py     # Invariant definitions
│   │
│   ├── motion/
│   │   ├── planner.py        # MotionPlanner
│   │   └── policies.py       # SAFE, DIRECT, Z_ONLY
│   │
│   ├── execution/
│   │   ├── executor.py       # CommandExecutor
│   │   ├── transport.py      # Serial/Mock transport
│   │   └── audit.py          # Command audit log
│   │
│   ├── workflow/
│   │   ├── machine.py        # State machine setup
│   │   ├── states.py         # State definitions
│   │   └── cycle.py          # PickPlaceCycle
│   │
│   └── api/
│       ├── app.py            # FastAPI app
│       └── routes/           # API routes
│
├── tests/
│   ├── unit/                 # Unit tests
│   ├── properties/           # Property-based tests
│   ├── integration/          # Integration tests
│   └── conftest.py           # Fixtures
│
├── specs/
│   ├── DESIGN.md             # This document
│   ├── INVARIANTS.md         # Formal invariant specs
│   └── API.md                # API specification
│
└── pyproject.toml            # Dependencies
```

---

## Next Steps

1. **Review this design** - Does it capture the failure modes you encountered?
2. **Pick frameworks** - Confirm `transitions` + `hypothesis`
3. **Write invariants first** - Tests before code
4. **Implement incrementally** - One layer at a time, green tests throughout
