# State Management

## Controller State

| State | Type | Initial | Updated By |
|-------|------|---------|------------|
| `_position` | Position | (0, 300, 0) | move_to, safe_move_to, pick_blade, place_blade, home, sync_position |
| `_is_homed` | bool | False | home() sets True |
| `_carrying_blade` | bool | False | pick_blade sets True, place_blade/home sets False |
| `_suction_active` | bool | False | suction_on/off, pick_blade, place_blade |
| `_motors_enabled` | bool | True | motors_on/off |
| `_planner.safe_z` | float | 50.0 | set_safe_z() |

## AppState (API layer)

| State | Type | Initial | Updated By |
|-------|------|---------|------------|
| `is_running` | bool | False | cycle run/stop |
| `is_paused` | bool | False | cycle pause/stop |
| `current_cycle` | int | 0 | cycle loop |
| `total_cycles` | int | 0 | cycle start |

## PositionStore (persisted)

| State | Type | Initial | Updated By |
|-------|------|---------|------------|
| `pick` | Position? | None | set_pick, set_pick_current |
| `safe_z` | float | 0 | set_safe_z, set_safe_z_current |
| `hooks` | list[Position] | [] | add_hook, delete_hook, clear_hooks |

## State Transition Diagram

```
DISCONNECTED
     │
     ▼ connect()
CONNECTED (not homed)
     │
     ▼ home()
HOMED ──────────────────────────────────────────┐
     │                                           │
     ├──► motors_off() ──► TEACH MODE           │
     │         │                                 │
     │         ▼ motors_on()                     │
     │    sync_position() ──► HOMED             │
     │                                           │
     ├──► pick_blade() ──► CARRYING BLADE       │
     │                          │                │
     │                          ▼ place_blade()  │
     │                       HOMED ◄─────────────┘
     │
     ▼ disconnect()
DISCONNECTED
```

## Safety Features

- **Position sync on teach mode exit**: M895 reads actual position from encoders
- **Auto-recovery**: Moving with motors disabled auto-enables and syncs
- **Pump safety**: Pump turns off on cycle error, stop, or completion
- **Workspace validation**: Positions validated before saving
- **Blade warning**: Log warning if entering teach mode while carrying blade
