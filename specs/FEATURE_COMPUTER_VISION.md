# Feature: Computer Vision (Future)

## Goal

Use camera to detect blade positions, count stacks, and verify hook placement.

## Status: Research Phase

This is a future enhancement requiring additional hardware and significant development.

## Hardware Required

- Rotrics Computer Vision Kit ($49) or compatible USB camera
- Mounting bracket (above workspace)
- Consistent lighting

## Potential Use Cases

### 1. Auto-Detect Stack Positions

```
Camera sees blade stacks → OpenCV finds contours → 
Calculate centroid → Convert pixel to XYZ → 
Auto-populate stack positions
```

**Benefit**: Zero manual teaching for stacks

### 2. Count Blades in Stack

```
Camera captures side view → Measure stack height →
Divide by blade thickness → Estimate count
```

**Benefit**: Accurate count without manual entry

### 3. Verify Hook Occupancy

```
Camera sees hook rail → Detect blade shapes →
Mark hooks as occupied/empty
```

**Benefit**: Skip occupied hooks, detect failures

### 4. Placement Verification

```
After place → Camera checks hook →
Blade present? Aligned correctly? →
Log result, retry if failed
```

**Benefit**: Quality control, error recovery

## Technical Approach

### Camera Calibration

```python
# Convert pixel coordinates to arm coordinates
class CameraCalibration:
    def __init__(self):
        # Calibration matrix from 4+ known points
        self.transform_matrix = None
    
    def calibrate(self, pixel_points: List, arm_points: List):
        """Compute transformation from pixel to arm coords."""
        # Use cv2.getPerspectiveTransform or similar
        pass
    
    def pixel_to_arm(self, px: int, py: int) -> Position:
        """Convert pixel coordinate to arm XYZ."""
        pass
```

### Blade Detection

```python
def detect_blades(frame) -> List[BladeBoundingBox]:
    # Convert to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Threshold or edge detection
    edges = cv2.Canny(gray, 50, 150)
    
    # Find contours
    contours, _ = cv2.findContours(edges, ...)
    
    # Filter by size/shape (rectangular, correct aspect ratio)
    blades = [c for c in contours if is_blade_shape(c)]
    
    return blades
```

### Integration Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Camera     │────▶│  Vision      │────▶│  Blade       │
│   (USB)      │     │  Service     │     │  Loader API  │
└──────────────┘     └──────────────┘     └──────────────┘
                           │
                           ▼
                     ┌──────────────┐
                     │  OpenCV +    │
                     │  ML Model    │
                     └──────────────┘
```

Vision runs as separate service, pushes detected positions to main API.

## Challenges

1. **Lighting consistency** - Shadows affect detection
2. **Camera mounting** - Must be stable, known position
3. **Calibration drift** - Need periodic recalibration
4. **Processing speed** - Real-time vs batch detection
5. **Blade variation** - Different sizes, colors, reflectivity

## Research Tasks

- [ ] Acquire Rotrics Vision Kit or USB camera
- [ ] Test basic OpenCV blade detection
- [ ] Prototype pixel-to-arm calibration
- [ ] Evaluate detection accuracy
- [ ] Determine if ML model needed vs simple CV

## Dependencies

- OpenCV (`pip install opencv-python`)
- NumPy
- Optional: TensorFlow/PyTorch for ML model

## Not In Scope (This Phase)

- Real-time tracking during movement
- Collision avoidance
- Dynamic obstacle detection

## Success Criteria (Research)

- [ ] Can detect blade stack location within 5mm
- [ ] Can count blades within ±2 accuracy
- [ ] Processing time < 500ms per frame
