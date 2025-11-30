# Feature: Multiple Blade Stacks

## Goal

Support multiple blade stacks so users can load different blade sizes in one session.

## Current State

- Single pick position stored in `blade_positions.json`
- All hooks pull from same pick location
- No concept of blade types

## Target State

- Multiple named stacks, each with position and blade count
- Each stack has a blade type (for future hook mapping)
- Stack count decrements on each pick
- Warning when stack is low/empty

## Data Model

```python
@dataclass
class PickStack:
    name: str                    # "stack_1", "small_blades", etc.
    position: Position           # XYZ of top of stack
    blade_type: str              # "default" for now, future: "small", "large"
    count: int                   # Blades remaining
    stack_height_mm: float       # Height per blade (for auto Z adjustment)
```

## Storage

```json
{
  "stacks": [
    {
      "name": "main",
      "position": {"x": -47, "y": 292, "z": -70},
      "blade_type": "default",
      "count": 20,
      "stack_height_mm": 2.0
    }
  ],
  "safe_z": 15.28,
  "hooks": [...]
}
```

## API Changes

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/stacks` | GET | List all stacks |
| `/api/stacks` | POST | Add new stack |
| `/api/stacks/{name}` | PUT | Update stack |
| `/api/stacks/{name}` | DELETE | Remove stack |
| `/api/stacks/{name}/teach` | POST | Set position from current |
| `/api/stacks/{name}/decrement` | POST | Reduce count by 1 |

## UI Changes

```
┌─────────────────────────────────────┐
│  BLADE STACKS                       │
├─────────────────────────────────────┤
│  [+ Add Stack]                      │
│                                     │
│  ▼ main (18 remaining)    [Delete]  │
│    Position: X=-47 Y=292 Z=-70      │
│    [Go To] [Teach Position]         │
│    Count: [18] [+][-]               │
└─────────────────────────────────────┘
```

## Tasks

- [ ] Create `PickStack` dataclass in `core/types.py`
- [ ] Update `PositionStore` to handle stacks list
- [ ] Migrate existing `pick` to `stacks[0]`
- [ ] Add stack API endpoints
- [ ] Update cycle runner to use stack
- [ ] Decrement count on successful pick
- [ ] Add stack management UI
- [ ] Warning when count reaches 0

## Migration

Existing `blade_positions.json` with `pick` field auto-migrates to:
```json
{
  "stacks": [{"name": "main", "position": <old pick>, "count": 99, ...}]
}
```

## Success Criteria

- [ ] Can define 2+ stacks with different positions
- [ ] Cycle picks from correct stack
- [ ] Count decrements after each pick
- [ ] UI shows stack status
