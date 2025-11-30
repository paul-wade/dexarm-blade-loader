# Tasks: DexArm Blade Loader Implementation

## Overview

Phased implementation with tests before code at each phase.

---

## Phase 0: Foundation (Current)

### ✅ Task 0.1: Documentation
- [x] Create dexarm-docs/ with command reference
- [x] Document custom Marlin firmware
- [x] Document common mistakes
- [x] Create requirements.md

### ✅ Task 0.2: Specs
- [x] Create design.md with architecture
- [x] Define invariants for PBT
- [ ] Create this tasks.md

---

## Phase 1: Core Types & Tests

### ✅ Task 1.1: Immutable Data Types (COMPLETE)

**File**: `backend/core/types.py`

**Tests**: `tests/unit/test_types.py` - **27 tests pass**

- [x] Position is immutable (frozen dataclass)
- [x] Position.distance_to() calculates correctly
- [x] Position.reach() calculates XY distance from origin
- [x] WorkspaceLimits.validate() rejects out-of-bounds
- [x] MoveCommand.to_gcode() produces valid G-code
- [x] MoveCommand requires at least one axis
- [x] All command types generate correct G-code

### ✅ Task 1.2: Motion Planner with PBT (COMPLETE)

**File**: `backend/core/planner.py`

**Tests**: `tests/properties/test_motion_invariants.py` - **12 PBT tests pass**

Invariants verified by Hypothesis (200 random inputs each):

- [x] INV-M1: Safe moves lift Z before XY motion
- [x] INV-M3: Wait (M400) after every move command
- [x] INV-M4: Rejects positions outside workspace
- [x] Pick/place sequences satisfy all invariants
- [x] Command axis detection works for all combinations

---

## Phase 2: Command Execution Layer

### ✅ Task 2.1: Command Queue (COMPLETE)

**File**: `backend/core/executor.py`

**Tests**: 8 tests pass

- [x] Commands enqueue and execute in order
- [x] History records all commands with timestamps
- [x] Queue clears after execution, history preserved
- [x] CommandResult tracks gcode, response, success

### ✅ Task 2.2: Transport Abstraction (COMPLETE)

**File**: `backend/core/transport.py`

**Tests**: 9 tests pass

- [x] Transport protocol defines interface
- [x] MockTransport simulates all DexArm responses
- [x] MockTransport tracks position through moves
- [x] M114 returns simulated position
- [x] Suction state simulated

---

## Phase 3: State Machine

### ✅ Task 3.1: Pick-Place Workflow (COMPLETE)

**File**: `backend/workflows/pick_place.py`

**Tests**: `tests/unit/test_workflow.py` - **14 tests pass**

- [x] States: IDLE → MOVING_TO_PICK → ... → COMPLETE
- [x] start() validates configuration
- [x] step() advances state and executes commands
- [x] run() executes full cycle
- [x] reset() returns to IDLE from any state
- [x] Callbacks: on_state_change, on_complete, on_error
- [x] Commands sent via CommandQueue
- [x] Position tracked throughout cycle

---

## Phase 4: Integration

### ✅ Task 4.1: Controller Facade (COMPLETE)

**File**: `backend/controller.py`

- [x] BladeLoaderController ties all components together
- [x] home(), move_to(), safe_move_to()
- [x] pick_blade(), place_blade()
- [x] State tracking: position, homed, carrying_blade
- [x] get_status(), get_command_history()

### ✅ Task 4.2: Integration Tests (COMPLETE)

**Tests**: `tests/integration/test_controller.py` - **17 tests pass**

- [x] Full pick-place cycle with MockTransport
- [x] Multiple cycles work
- [x] Position tracking stays in sync with transport
- [x] Command history recorded
- [x] Error handling (move before home, place without pick)

---

## Phase 5: API & UI

### ✅ Task 5.1: FastAPI Endpoints (COMPLETE)

All routes updated to use `BladeLoaderController`.

**Connection** (`/api`):
- [x] GET /ports - List serial ports
- [x] GET /status - Full robot status
- [x] GET /history - Command audit trail
- [x] POST /connect - Connect to robot
- [x] POST /disconnect

**Movement** (`/api`):
- [x] POST /home - Home the arm (M1112)
- [x] POST /move - Direct move
- [x] POST /safe_move - Safe move (Z-up first)
- [x] POST /jog - Jog single axis
- [x] POST /teach/enable - Motors off
- [x] POST /teach/disable - Motors on
- [x] POST /estop - Emergency stop (M410)
- [x] GET /position

**Cycles** (`/api/cycle`):
- [x] POST /pick - Pick from position
- [x] POST /place - Place at position
- [x] POST /pick_from_stored - Pick from saved position
- [x] POST /place_at_hook/{n} - Place at hook N
- [x] POST /run - Full cycle all hooks
- [x] POST /stop - Stop cycle
- [x] GET /state

**Suction** (`/api/suction`):
- [x] POST /on - M1000
- [x] POST /off - M1003
- [x] POST /blow - M1001
- [x] POST /release - M1002

### ✅ Task 5.2: React UI Updates (COMPLETE)

- [x] Updated Status interface for new API response
- [x] Added homed, carrying_blade, current_cycle status
- [x] Fixed suction endpoints (/suction/on)
- [x] Fixed cycle endpoint (/cycle/run)
- [x] Progress bar shows current/total cycles
- [x] Status shows "Ready" when homed

### ✅ Task 5.3: API Tests (COMPLETE)

**Tests**: `tests/api/test_endpoints.py` - **25 tests pass**

- [x] Connection endpoints
- [x] Movement endpoints (home, move, jog)
- [x] Cycle endpoints (pick, place)
- [x] Suction endpoints
- [x] History endpoint

---

## Test Commands

```bash
# Run all tests
pytest tests/ -v

# Run only PBT tests
pytest tests/properties/ -v

# Run with coverage
pytest tests/ --cov=backend --cov-report=html

# Run specific invariant test
pytest tests/properties/test_motion_invariants.py::test_safe_move_lifts_before_xy -v
```

---

## Definition of Done

Each task is complete when:

1. ✅ Code implements the spec
2. ✅ Unit tests pass
3. ✅ PBT tests pass (where applicable)
4. ✅ Type hints added
5. ✅ Docstrings added
6. ✅ No regressions in existing tests
