# Motion System Invariants

These invariants MUST hold at all times. Property-based tests verify them.

---

## Motion Safety Invariants

### INV-M1: Safe Move Sequence

**Statement**: A safe move from position A to position B must:
1. First lift Z to safe_z (if current Z < safe_z)
2. Then move XY to target XY
3. Then lower Z to target Z

**Formal**:
```
safe_move(current, target, safe_z) →
  IF current.z < safe_z THEN
    emit(MOVE_Z(safe_z)) BEFORE any_xy_move
  emit(MOVE_XY(target.x, target.y)) BEFORE lower_z
  IF target.z < safe_z THEN
    emit(MOVE_Z(target.z)) LAST
```

**Test Strategy**: Generate random (current, target, safe_z), verify command sequence.

---

### INV-M2: No Low XY With Blade

**Statement**: While carrying a blade, the arm must not move XY if Z < safe_z.

**Formal**:
```
∀ command c IN execution_sequence:
  IF state.carrying_blade AND state.z < state.safe_z THEN
    NOT c.changes_xy()
```

**Test Strategy**: Simulate cycles, inject faults, verify invariant holds.

---

### INV-M3: Move Commands Wait for Completion

**Statement**: Every move command must be followed by M400 (wait) before any subsequent command that depends on position.

**Formal**:
```
∀ command c IN execution_sequence:
  IF c.is_move() THEN
    next_position_dependent(c) IMPLIES has_wait_between(c, next_position_dependent(c))
```

**Test Strategy**: Analyze command logs, verify wait commands present.

---

### INV-M4: Position Within Workspace

**Statement**: All commanded positions must be within the DexArm workspace.

**Formal**:
```
∀ position p IN commanded_positions:
  -200 ≤ p.x ≤ 200
  100 ≤ p.y ≤ 400  
  -50 ≤ p.z ≤ 200
  sqrt(p.x² + p.y²) ≤ 320  # Reach limit
```

**Test Strategy**: Generate random positions, verify validation rejects invalid.

---

## State Machine Invariants

### INV-S1: Valid State Transitions

**Statement**: State transitions must follow the defined state graph.

**Formal**:
```
valid_transitions = {
  IDLE: [LIFTING_TO_SAFE],
  LIFTING_TO_SAFE: [MOVING_XY_ABOVE_PICK, ERROR],
  MOVING_XY_ABOVE_PICK: [ACTIVATING_SUCTION, ERROR],
  ACTIVATING_SUCTION: [LOWERING_TO_PICK, ERROR],
  LOWERING_TO_PICK: [GRABBING, ERROR],
  GRABBING: [LIFTING_WITH_BLADE, ERROR],
  LIFTING_WITH_BLADE: [MOVING_XY_ABOVE_HOOK, ERROR],
  MOVING_XY_ABOVE_HOOK: [LOWERING_TO_HOOK, ERROR],
  LOWERING_TO_HOOK: [RELEASING, ERROR],
  RELEASING: [LIFTING_FROM_HOOK, ERROR],
  LIFTING_FROM_HOOK: [LIFTING_TO_SAFE, HOMING, ERROR],  # Loop or finish
  HOMING: [IDLE, ERROR],
  ERROR: [IDLE, RECOVERING]
}

∀ transition (s1 → s2) IN state_history:
  s2 IN valid_transitions[s1]
```

**Test Strategy**: Run simulated cycles, verify all transitions are valid.

---

### INV-S2: Suction State Consistency

**Statement**: Suction state must be consistent with blade carrying state.

**Formal**:
```
∀ state s:
  s.carrying_blade IMPLIES s.suction == ON
  s IN {GRABBING, LIFTING_WITH_BLADE, MOVING_XY_ABOVE_HOOK, LOWERING_TO_HOOK} 
    IMPLIES s.carrying_blade
```

**Test Strategy**: Track suction commands alongside state, verify consistency.

---

### INV-S3: No State Regression

**Statement**: Within a single cycle, certain states cannot be revisited after leaving.

**Formal**:
```
visited_states = []
∀ state s IN cycle_execution:
  IF s IN {GRABBING, RELEASING} THEN
    s NOT IN visited_states  # Can't re-grab or re-release in same blade operation
  visited_states.append(s)
```

**Test Strategy**: Track visited states, detect regressions.

---

## Position Tracking Invariants

### INV-P1: Position Sync After Move

**Statement**: After any move command completes, tracked position must match actual within tolerance.

**Formal**:
```
∀ move_complete event:
  |tracked.x - actual.x| < 0.5mm
  |tracked.y - actual.y| < 0.5mm
  |tracked.z - actual.z| < 0.5mm
```

**Test Strategy**: Compare tracked vs encoder position after moves.

---

### INV-P2: Position Update Atomicity

**Statement**: Position updates must be atomic (all axes or none).

**Formal**:
```
∀ position_update u:
  (u.x_updated AND u.y_updated AND u.z_updated) OR
  (NOT u.x_updated AND NOT u.y_updated AND NOT u.z_updated)
```

**Test Strategy**: Concurrent access tests, verify no partial updates.

---

### INV-P3: Position Monotonic During Safe Move

**Statement**: During a safe move sequence, Z must be monotonically non-decreasing until XY move completes.

**Formal**:
```
∀ safe_move_sequence seq:
  ∀ i, j WHERE i < j AND j < first_xy_complete:
    seq[j].z ≥ seq[i].z
```

**Test Strategy**: Log position at each command, verify monotonicity.

---

## Recovery Invariants

### INV-R1: Safe State After Error

**Statement**: After any error recovery, the arm must be in a safe state.

**Formal**:
```
∀ error_recovery event:
  post_state.z ≥ safe_z
  post_state.suction == OFF
  post_state.motors == ENABLED
```

**Test Strategy**: Inject errors at various points, verify recovery state.

---

### INV-R2: Position Re-Sync After Error

**Statement**: After error recovery, position must be re-synced from encoder.

**Formal**:
```
∀ error_recovery event:
  read_encoder() called before next_move
  tracked_position == encoder_position
```

**Test Strategy**: Inject position drift, trigger error, verify re-sync.

---

## Command Audit Invariants

### INV-A1: Complete Audit Trail

**Statement**: Every command sent to the arm must be logged.

**Formal**:
```
∀ command c sent via transport:
  c IN audit_log
  audit_log[c].timestamp ≤ now()
  audit_log[c].response recorded
```

**Test Strategy**: Compare transport calls to audit log.

---

### INV-A2: Command Order Preserved

**Statement**: Audit log order matches execution order.

**Formal**:
```
∀ commands c1, c2 WHERE c1 sent_before c2:
  audit_log.index(c1) < audit_log.index(c2)
```

**Test Strategy**: Verify log order matches send order.

---

## Test Generation Strategies

### Hypothesis Strategies for Position

```python
from hypothesis import strategies as st

# Valid position within workspace
valid_position = st.builds(
    Position,
    x=st.floats(-150, 150),
    y=st.floats(150, 350),
    z=st.floats(-30, 150)
).filter(lambda p: (p.x**2 + p.y**2)**0.5 <= 300)

# Safe Z values
safe_z_strategy = st.floats(10, 100)

# Random sequence of positions (for cycle simulation)
position_sequence = st.lists(valid_position, min_size=1, max_size=10)
```

### Hypothesis Strategies for Commands

```python
# Move commands
move_command = st.builds(
    MoveCommand,
    x=st.one_of(st.none(), st.floats(-150, 150)),
    y=st.one_of(st.none(), st.floats(150, 350)),
    z=st.one_of(st.none(), st.floats(-30, 150)),
    feedrate=st.sampled_from([1000, 2000, 3000])
)

# Command sequences
command_sequence = st.lists(
    st.one_of(
        move_command,
        st.just(WaitCommand()),
        st.builds(SuctionCommand, action=st.sampled_from(["on", "release", "off"]))
    ),
    min_size=1,
    max_size=50
)
```

---

## Invariant Priority

| Priority | Invariant | Failure Impact |
|----------|-----------|----------------|
| P0 (Critical) | INV-M1 (Safe Move) | Blade drop, collision |
| P0 (Critical) | INV-M2 (No Low XY) | Blade drop |
| P0 (Critical) | INV-M4 (Workspace) | Arm damage |
| P1 (High) | INV-S1 (State Transitions) | Undefined behavior |
| P1 (High) | INV-R1 (Safe After Error) | Unsafe state |
| P2 (Medium) | INV-P1 (Position Sync) | Drift, missed picks |
| P2 (Medium) | INV-M3 (Wait Commands) | Race conditions |
| P3 (Low) | INV-A1 (Audit Trail) | Debug difficulty |
