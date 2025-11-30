# Requirements: DexArm Blade Loader

## Overview

Build a reliable robotic blade loader system using the DexArm robot arm with pneumatic suction module.

## Problem Statement

Previous implementations suffered from:
- Inconsistent motion patterns (sometimes lifts for safety, sometimes doesn't)
- Wrong G-code commands (M112 vs M1112, encoder values misused)
- No single source of truth for arm position
- No tests to verify motion safety invariants
- Scattered logic without clear orchestration

## Goals

1. **Reliable motion** - Every move follows defined safety patterns
2. **Testable** - Property-based tests verify invariants hold for ANY input
3. **Observable** - Clear audit trail of all commands sent
4. **Recoverable** - Handle errors gracefully, return to safe state

---

## Functional Requirements

### FR-1: Motion Control

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1.1 | System MUST lift Z to safe height before any XY movement when carrying blade | P0 |
| FR-1.2 | System MUST wait for move completion (M400) before reading position | P0 |
| FR-1.3 | System MUST send M1112 (home) on startup, never M112 | P0 |
| FR-1.4 | System MUST validate all positions against workspace limits before moving | P0 |
| FR-1.5 | System MUST use Cartesian coordinates (G1), never encoder values (M894) for normal moves | P0 |
| FR-1.6 | System SHOULD support configurable safe_z height | P1 |
| FR-1.7 | System SHOULD support configurable feedrate | P1 |

### FR-2: Suction Control

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-2.1 | System MUST activate suction (M1000) BEFORE lowering to pick | P0 |
| FR-2.2 | System MUST wait for vacuum before lifting (configurable delay) | P0 |
| FR-2.3 | System MUST release suction (M1002) BEFORE lifting from place position | P0 |
| FR-2.4 | System MUST stop pump (M1003) after release | P1 |

### FR-3: Position Tracking

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-3.1 | System MUST track commanded position internally | P0 |
| FR-3.2 | System MUST verify actual position matches expected after critical moves | P1 |
| FR-3.3 | System SHOULD sync position from arm (M114) periodically | P2 |

### FR-4: State Management

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-4.1 | System MUST track whether blade is being carried | P0 |
| FR-4.2 | System MUST track suction state (on/off/released) | P0 |
| FR-4.3 | System MUST prevent XY moves at low Z when carrying blade | P0 |

### FR-5: Error Handling

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-5.1 | System MUST detect communication errors | P0 |
| FR-5.2 | System MUST return to safe state on error | P0 |
| FR-5.3 | System SHOULD support emergency stop (M410) | P1 |
| FR-5.4 | System MUST NOT use M112 (unrecoverable stop) except in true emergency | P0 |

---

## Non-Functional Requirements

### NFR-1: Testability

| ID | Requirement | Priority |
|----|-------------|----------|
| NFR-1.1 | All motion logic MUST be testable without hardware | P0 |
| NFR-1.2 | System MUST support mock transport for testing | P0 |
| NFR-1.3 | System MUST have property-based tests for motion invariants | P0 |

### NFR-2: Observability

| ID | Requirement | Priority |
|----|-------------|----------|
| NFR-2.1 | All commands sent MUST be logged | P0 |
| NFR-2.2 | State transitions MUST be observable | P1 |

### NFR-3: Maintainability

| ID | Requirement | Priority |
|----|-------------|----------|
| NFR-3.1 | Motion planning MUST be separate from command execution | P0 |
| NFR-3.2 | Command generation MUST be separate from serial transport | P0 |
| NFR-3.3 | Code MUST use type hints | P1 |

---

## Constraints

1. **Hardware**: DexArm with custom Marlin firmware
2. **Communication**: Serial 115200 baud, wait for "ok" after each command
3. **Workspace**: X ±200mm, Y 100-400mm, Z -60 to 200mm, reach ≤320mm
4. **Home position**: X=0, Y=300, Z=0

---

## Success Criteria

1. ✅ 100+ property-based test cases pass
2. ✅ Motion invariants verified for random inputs
3. ✅ No crashes during 100 pick-place cycles
4. ✅ All commands logged and auditable
5. ✅ Recovery from simulated errors works
