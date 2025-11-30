# Feature: Geometry-Based Position Calculator

## Goal

Calculate hook/stack positions from known physical dimensions instead of teaching every position by hand.

## Depends On

- FEATURE_MULTI_STACK.md

## Current State

- Every position manually taught
- Time-consuming setup
- Error-prone if tray moves

## Target State

- Define physical reference points (tray origin, hook rail origin)
- Enter grid dimensions and spacing
- Auto-generate positions mathematically
- Fine-tune with teach mode if needed

## Concept

```
Known: Tray is at X=-100, Y=250
Known: Blade width is 20mm, gap is 5mm
Calculate: Stack 0 at X=-100, Stack 1 at X=-75, Stack 2 at X=-50...

Known: Hook rail starts at X=100, Y=320
Known: Hook spacing is 25mm
Calculate: Hook 0 at X=100, Hook 1 at X=125, Hook 2 at X=150...
```

## Data Model

```python
@dataclass
class GeometryConfig:
    # Tray reference
    tray_origin: Position        # Corner of blade tray
    blade_width_mm: float
    blade_length_mm: float
    tray_gap_mm: float           # Gap between blades in tray
    
    # Hook rail reference  
    rail_origin: Position        # Start of hook rail
    hook_spacing_mm: float       # Distance between hooks
    
@dataclass
class CalculatedPosition:
    position: Position
    source: str                  # "calculated" or "taught"
    offset: Position             # Fine-tune offset from calculated
```

## Calculator

```python
class GeometryCalculator:
    def __init__(self, config: GeometryConfig):
        self.config = config
    
    def stack_position(self, row: int, col: int) -> Position:
        """Calculate stack position from grid index."""
        x = self.config.tray_origin.x + col * (self.config.blade_width_mm + self.config.tray_gap_mm)
        y = self.config.tray_origin.y + row * (self.config.blade_length_mm + self.config.tray_gap_mm)
        z = self.config.tray_origin.z
        return Position(x, y, z)
    
    def hook_position(self, index: int) -> Position:
        """Calculate hook position from index on rail."""
        x = self.config.rail_origin.x + index * self.config.hook_spacing_mm
        y = self.config.rail_origin.y
        z = self.config.rail_origin.z
        return Position(x, y, z)
```

## Calibration Workflow

1. **Teach reference points**
   - Move arm to tray corner → "Set Tray Origin"
   - Move arm to first hook → "Set Rail Origin"

2. **Enter dimensions**
   - Blade size, tray gap
   - Hook spacing

3. **Generate positions**
   - Click "Calculate 5 Hooks"
   - Positions appear in list

4. **Verify and fine-tune**
   - "Go To Hook 1" → visually check
   - If off, teach correction offset

## UI

```
┌─────────────────────────────────────┐
│  GEOMETRY SETUP                     │
├─────────────────────────────────────┤
│  Tray Origin: X=-100 Y=250 Z=-70    │
│  [Teach Current Position]           │
│                                     │
│  Blade Width: [20] mm               │
│  Blade Length: [60] mm              │
│  Tray Gap: [5] mm                   │
├─────────────────────────────────────┤
│  Rail Origin: X=100 Y=320 Z=-20     │
│  [Teach Current Position]           │
│                                     │
│  Hook Spacing: [25] mm              │
├─────────────────────────────────────┤
│  Generate: [3] stacks  [5] hooks    │
│  [Calculate Positions]              │
└─────────────────────────────────────┘
```

## Tasks

- [ ] Create `GeometryConfig` dataclass
- [ ] Create `GeometryCalculator` class
- [ ] API endpoint to set reference points
- [ ] API endpoint to generate positions
- [ ] Store geometry config in JSON
- [ ] UI for geometry setup
- [ ] Fine-tune offset support

## Success Criteria

- [ ] Can set tray and rail origins by teaching
- [ ] Calculated positions within 2mm of actual
- [ ] Generated hooks work without manual adjustment
