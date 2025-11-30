# Feature: Computer Vision (Future)

## Goal

Use camera to detect blade positions, count stacks, and verify hook placement.

## Status: Research Phase

This is a future enhancement requiring additional hardware and significant development.

## Hardware Required

- Rotrics Computer Vision Kit ($49) or compatible USB camera
- Mounting bracket (above workspace)
- Consistent lighting

## Practical Use Cases

Given physical constraints (thin blades, opaque container sides), focus on **top-down detection**:

### 1. Stack Empty vs Has Blades (Top-Down)

```
Camera above stack → See shiny blade surface vs dark container bottom
├─ Blade visible = stack has blades
└─ Dark/black = stack empty → ALERT USER
```

**Detection**: Simple brightness threshold on stack region
**Benefit**: Know when to refill before cycle fails

### 2. Hook Occupied vs Empty

```
Camera sees hook rail from above/angle →
├─ Hook has blade = rectangular bright shape
└─ Hook empty = just the hook (thin line or nothing)
```

**Detection**: Look for blade-sized bright rectangle at each hook position
**Benefit**: 
- Skip already-occupied hooks
- Verify placement succeeded
- Detect dropped blades

### 3. Placement Verification (After Each Place)

```
Place blade on hook → Wait 500ms → Capture image →
├─ Blade detected at hook = SUCCESS
└─ No blade detected = FAILED (retry or alert)
```

**Benefit**: Catch failures immediately, not at end of cycle

### 4. Cycle Pre-Check

```
Before starting cycle:
├─ Check all target hooks are empty
├─ Check stack has blades  
└─ If issues → Alert user before wasting time
```

## What We CAN'T Easily Detect

- **Exact blade count** (too thin to see stack height)
- **Blade orientation** (need rotary module feedback instead)
- **Blade quality/defects** (maybe GPT-4V could help here)

## Technical Approaches

### Option 1: Classical CV (OpenCV)

**Best for**: High contrast scenarios (shiny blade on dark background)

```python
def detect_blades_opencv(frame) -> List[BladeBoundingBox]:
    # Shiny metal on dark background = high contrast
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Threshold - bright metal vs dark container
    _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
    
    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter by aspect ratio (blades are rectangular)
    blades = [c for c in contours if is_blade_shape(c)]
    return blades

def is_blade_shape(contour) -> bool:
    """Check if contour matches blade dimensions."""
    rect = cv2.minAreaRect(contour)
    w, h = rect[1]
    aspect = max(w,h) / min(w,h) if min(w,h) > 0 else 0
    return 2.5 < aspect < 4.0  # Blade aspect ratio
```

**Pros**: Fast, no API costs, works offline
**Cons**: Sensitive to lighting, needs tuning

### Option 2: OpenAI Vision API (GPT-4V)

**Best for**: Complex scenes, natural language queries, no training needed

```python
import openai
import base64

def analyze_workspace_gpt4v(image_path: str, query: str) -> dict:
    """Use GPT-4V to analyze workspace image."""
    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode()
    
    response = openai.chat.completions.create(
        model="gpt-4-vision-preview",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": query},
                {"type": "image_url", "image_url": {
                    "url": f"data:image/jpeg;base64,{image_b64}"
                }}
            ]
        }],
        max_tokens=500
    )
    return response.choices[0].message.content

# Example queries:
# "How many blades are in the stack on the left?"
# "Is hook #3 occupied? Describe what you see."
# "Are all blades aligned correctly on the hooks?"
# "Estimate the XY position of the blade stack center"
```

**Pros**: 
- Zero training - works out of the box
- Natural language queries
- Can describe anomalies ("blade is crooked")
- Handles varied lighting

**Cons**:
- API cost (~$0.01-0.03 per image)
- Latency (1-3 seconds)
- Requires internet
- Position estimates less precise than CV

### Option 3: Custom Trained Model (YOLO/etc)

**Best for**: Production, high accuracy, offline

```python
# Training workflow:
# 1. Capture 50-100 images of workspace
# 2. Label with tool like LabelImg or Roboflow
# 3. Train YOLO model
# 4. Deploy locally

from ultralytics import YOLO

model = YOLO("blade_detector.pt")  # Your trained model

def detect_blades_yolo(frame):
    results = model(frame)
    return results[0].boxes  # Bounding boxes with confidence
```

**Training the model:**
1. **Capture images** - Various lighting, stack heights, angles
2. **Label them** - Draw boxes around blades, hooks, etc.
3. **Use Roboflow** - Free tier, handles labeling + training
4. **Export model** - Download .pt file for local inference

### Option 4: Hybrid Approach (Recommended)

```python
class HybridVision:
    def __init__(self):
        self.opencv = OpenCVDetector()
        self.gpt4v = GPT4VAnalyzer()
    
    def quick_count(self, frame) -> int:
        """Fast local count with OpenCV."""
        return len(self.opencv.detect_blades(frame))
    
    def verify_placement(self, frame, hook_index: int) -> dict:
        """Use GPT-4V for verification and troubleshooting."""
        return self.gpt4v.analyze(frame, 
            f"Is hook #{hook_index} correctly loaded? Is the blade aligned?")
    
    def diagnose_problem(self, frame) -> str:
        """Natural language diagnosis when something goes wrong."""
        return self.gpt4v.analyze(frame,
            "Describe any problems you see with the blade placement.")
```

## Why Dark Background Helps

```
┌─────────────────────────────────────┐
│  SHINY BLADE ON BLACK CONTAINER    │
├─────────────────────────────────────┤
│                                     │
│   ████████████  ← Blade reflects   │
│   ████████████    light (bright)   │
│   ████████████                     │
│   ▓▓▓▓▓▓▓▓▓▓▓▓  ← Dark container  │
│   ▓▓▓▓▓▓▓▓▓▓▓▓    (low values)    │
│                                     │
│   Simple threshold separates them!  │
└─────────────────────────────────────┘
```

The black container you mentioned is perfect - high contrast = easy detection.

## Camera Calibration

```python
class CameraCalibration:
    """Convert pixel coordinates to arm XYZ."""
    
    def __init__(self):
        self.transform_matrix = None
    
    def calibrate(self, pixel_points: List, arm_points: List):
        """
        Calibrate using 4+ known points.
        Move arm to known positions, mark pixel locations.
        """
        # pixel_points: [(px1,py1), (px2,py2), ...]
        # arm_points: [(x1,y1), (x2,y2), ...]
        self.transform_matrix = cv2.getPerspectiveTransform(
            np.float32(pixel_points),
            np.float32(arm_points)
        )
    
    def pixel_to_arm(self, px: int, py: int) -> Tuple[float, float]:
        """Convert pixel to arm XY coordinates."""
        point = np.float32([[px, py]])
        transformed = cv2.perspectiveTransform(point, self.transform_matrix)
        return transformed[0][0], transformed[0][1]
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
