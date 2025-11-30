# Feature: Hook-to-Stack Mapping

## Goal

Each hook specifies which blade stack to pull from, enabling mixed blade sizes on one hook rail.

## Depends On

- FEATURE_MULTI_STACK.md (must have multiple stacks first)

## Current State

- Hooks only store position
- All hooks implicitly use the single pick location
- No blade type concept

## Target State

- Each hook has a `stack_name` field
- Cycle picks from the correct stack for each hook
- Skip hooks if their stack is empty
- Validation: hook's stack must exist

## Data Model

```python
@dataclass
class Hook:
    position: Position
    stack_name: str              # Which stack to pull from
    occupied: bool = False       # Has a blade on it (future)
```

## Storage

```json
{
  "hooks": [
    {
      "position": {"x": 150, "y": 320, "z": -20},
      "stack_name": "main"
    },
    {
      "position": {"x": 175, "y": 320, "z": -20},
      "stack_name": "large_blades"
    }
  ]
}
```

## Cycle Logic

```python
for hook in hooks:
    stack = get_stack(hook.stack_name)
    if stack.count == 0:
        log_warn(f"Skipping hook, stack '{hook.stack_name}' empty")
        continue
    
    pick_blade(stack.position)
    stack.count -= 1
    place_blade(hook.position)
```

## UI Changes

```
┌─────────────────────────────────────┐
│  HOOKS                              │
├─────────────────────────────────────┤
│  Hook 1: [main ▼]         [Delete]  │
│    Position: X=150 Y=320 Z=-20      │
│    [Go To] [Teach Position]         │
│                                     │
│  Hook 2: [large_blades ▼] [Delete]  │
│    Position: X=175 Y=320 Z=-20      │
│    [Go To] [Teach Position]         │
└─────────────────────────────────────┘
```

Dropdown shows available stack names.

## Tasks

- [ ] Add `stack_name` field to Hook dataclass
- [ ] Update hook API to include stack_name
- [ ] Validate stack_name exists on hook add/update
- [ ] Update cycle runner to pick from correct stack
- [ ] Skip hooks with empty stacks (log warning)
- [ ] Add stack selector dropdown in UI

## Migration

Existing hooks without `stack_name` default to first stack:
```python
hook.stack_name = hook.get("stack_name", stacks[0].name)
```

## Success Criteria

- [ ] Can assign different stacks to different hooks
- [ ] Cycle picks correct blade for each hook
- [ ] Empty stack causes skip, not crash
