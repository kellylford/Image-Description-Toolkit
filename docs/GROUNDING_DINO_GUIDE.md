# GroundingDINO Implementation Guide

## 🎯 What Makes GroundingDINO Special

### YOLO vs GroundingDINO

**YOLO (Current)**:
```python
# YOLO can ONLY detect these 80 classes:
"person", "bicycle", "car", "motorcycle", "airplane", "bus", 
"train", "truck", "boat", "traffic light", "fire hydrant", 
"stop sign", "parking meter", "bench", "bird", "cat", "dog",
"horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe",
# ... 80 total classes
```

**GroundingDINO (Proposed)**:
```python
# Can detect ANYTHING you describe:
"red cars"
"people wearing safety vests"
"damaged equipment"
"exit signs"
"wooden furniture"
"objects on fire"
"people not wearing masks"
"animals in distress"
# INFINITE possibilities!
```

---

## 🔍 How It Works

### Basic Workflow

```python
from groundingdino.util.inference import load_model, predict

# 1. Load model (one time)
model = load_model(
    config_path="GroundingDINO/groundingdino/config/GroundingDINO_SwinT_OGC.py",
    checkpoint_path="weights/groundingdino_swint_ogc.pth"
)

# 2. Define what you're looking for
TEXT_PROMPT = "people . cars . bicycles"  # Note: Use periods (.) as separators

# 3. Run detection
boxes, logits, phrases = predict(
    model=model,
    image=image,
    caption=TEXT_PROMPT,
    box_threshold=0.35,  # Confidence threshold
    text_threshold=0.25   # Text matching threshold
)

# 4. Get results
# boxes: [[x1, y1, x2, y2], ...] - bounding box coordinates
# logits: [0.95, 0.87, ...] - confidence scores
# phrases: ["people", "car", "bicycle"] - detected labels
```

---

## 🎨 Default Detection Strategy

### Option 1: Comprehensive Default Scan

Run with a broad prompt to catch everything:

```python
DEFAULT_PROMPT = (
    "objects . people . animals . vehicles . furniture . "
    "electronics . text . signs . tools . plants . "
    "clothing . food . buildings . outdoor . indoor"
)
```

**Returns**: All major categories of objects found in the image.

**Example Output**:
```
Detected objects:
- people (3 instances, confidence: 0.92, 0.89, 0.87)
- laptop (1 instance, confidence: 0.94)
- coffee cup (2 instances, confidence: 0.81, 0.76)
- chair (4 instances, confidence: 0.88, 0.85, 0.83, 0.79)
- window (2 instances, confidence: 0.91, 0.89)
```

---

### Option 2: Category-Specific Defaults

Different default prompts for different image types:

```python
DEFAULTS = {
    "general": "objects . people . animals . vehicles",
    
    "indoor": "people . furniture . electronics . decorations . "
              "appliances . lighting . windows . doors",
    
    "outdoor": "people . vehicles . buildings . trees . sky . "
               "roads . signs . animals . landscape",
    
    "workplace": "people . computers . desks . chairs . equipment . "
                 "safety gear . tools . machinery",
    
    "retail": "products . shelves . people . checkout . displays . "
              "signage . packaging",
    
    "safety": "fire extinguisher . exit signs . safety equipment . "
              "hazards . emergency lights . first aid",
    
    "document": "text . logos . diagrams . tables . images . "
                "signatures . stamps . barcodes"
}
```

---

## 🔄 Two-Stage Workflow

### Stage 1: Default Detection

```python
# Run comprehensive scan
default_prompt = "objects . people . animals . vehicles . furniture . electronics"
detections = grounding_dino.detect(image, default_prompt)

# Show user what was found
print("Found in image:")
for detection in detections:
    print(f"  - {detection.label}: {detection.count} instance(s)")
```

**Example Output**:
```
Found in image:
  - people: 3 instance(s)
  - laptop: 1 instance(s)  
  - chair: 4 instance(s)
  - coffee cup: 2 instance(s)
  - plant: 1 instance(s)
```

### Stage 2: User Refinement (Optional)

User can then ask specific questions:

```python
# User asks: "Show me just the people"
refined_prompt = "people"
people_detections = grounding_dino.detect(image, refined_prompt)

# User asks: "Are there any red objects?"
refined_prompt = "red objects"
red_detections = grounding_dino.detect(image, refined_prompt)

# User asks: "Find safety equipment"
refined_prompt = "safety equipment . hard hat . safety vest . fire extinguisher"
safety_detections = grounding_dino.detect(image, refined_prompt)
```

---

## 🎯 Integration with Ollama (Hybrid Mode)

### Approach 1: Detection-Enhanced Description

```python
# 1. Run GroundingDINO default scan
detections = grounding_dino.detect(image, DEFAULT_PROMPT)

# 2. Format detection results
detection_summary = format_detections(detections)
# "Detected: 3 people, 1 laptop, 4 chairs, 2 coffee cups, 1 plant"

# 3. Pass to Ollama with context
ollama_prompt = f"""
Describe this image in detail. The following objects were detected:
{detection_summary}

Please provide a comprehensive description that incorporates these detected objects.
"""

description = ollama.describe(image, ollama_prompt)
```

**Result**:
```
"The image shows an office meeting room with three people seated around a table. 
There are four chairs, suggesting room for additional participants. A laptop is 
open on the table, likely being used for a presentation. Two coffee cups indicate 
this might be a morning meeting. A decorative plant in the corner adds a touch 
of greenery to the professional environment."
```

### Approach 2: Progressive Refinement

```python
# 1. Get basic description from Ollama
basic_description = ollama.describe(image, "Describe this image briefly")

# 2. Based on description, run targeted GroundingDINO queries
if "office" in basic_description.lower():
    prompts = ["people . furniture . electronics"]
elif "outdoor" in basic_description.lower():
    prompts = ["people . vehicles . buildings . nature"]
elif "retail" in basic_description.lower():
    prompts = ["products . shelves . people . signage"]

# 3. Combine results
detections = grounding_dino.detect(image, prompts[0])
final_description = ollama.describe(
    image, 
    f"Enhance this description with details: {basic_description}\n"
    f"Objects detected: {format_detections(detections)}"
)
```

---

## 🎮 User Interface Options

### Option A: Automatic Mode (Default)

```
[Process Images Dialog]

Provider: GroundingDINO + Ollama

Detection Mode: 
  (*) Automatic (comprehensive scan)
  ( ) Custom query
  
Confidence Threshold: [===|===] 0.35

[Process Selected]
```

Runs with default comprehensive prompt, combines with Ollama.

### Option B: Custom Query Mode

```
[Process Images Dialog]

Provider: GroundingDINO + Ollama

Detection Mode:
  ( ) Automatic (comprehensive scan)
  (*) Custom query
  
Query: [find all safety equipment            ]

Examples:
  - "red objects"
  - "people wearing hats"  
  - "damaged items"
  - "text . signs . labels"

[Process Selected]
```

User types exactly what they want to find.

### Option C: Interactive Refinement

```
[After initial processing]

Initial Detection Results:
✓ 3 people detected
✓ 1 laptop detected
✓ 4 chairs detected

Refine search:
[find specific objects...           ] [Search]

Or use quick filters:
[People Only] [Electronics] [Furniture] [Custom...]
```

User can refine after seeing initial results.

---

## 🔧 Implementation Architecture

### Provider Structure

```python
class GroundingDINOProvider(AIProvider):
    """Text-prompted zero-shot object detection"""
    
    def __init__(self):
        self.model = None
        self.default_prompts = {
            'comprehensive': "objects . people . animals . vehicles . furniture",
            'indoor': "people . furniture . electronics . decorations",
            'outdoor': "people . vehicles . buildings . nature",
            # ... more presets
        }
    
    def is_available(self):
        try:
            import groundingdino
            return True
        except ImportError:
            return False
    
    def get_available_models(self):
        return [
            "Comprehensive Detection (Auto)",
            "Indoor Scene Detection",
            "Outdoor Scene Detection", 
            "Workplace Safety Detection",
            "Custom Query (User-Defined)"
        ]
    
    def describe_image(self, image_path, prompt, model, custom_query=None):
        # Load model if needed
        if self.model is None:
            self.model = self._load_model()
        
        # Determine detection prompt
        if custom_query:
            detection_prompt = custom_query
        else:
            detection_prompt = self._get_prompt_for_model(model)
        
        # Run detection
        detections = self._detect_objects(image_path, detection_prompt)
        
        # Format results
        return self._format_detections(detections)
    
    def _detect_objects(self, image_path, prompt):
        """Run GroundingDINO detection"""
        # Load image
        image = load_image(image_path)
        
        # Run prediction
        boxes, logits, phrases = predict(
            model=self.model,
            image=image,
            caption=prompt,
            box_threshold=0.35,
            text_threshold=0.25
        )
        
        # Format results
        detections = []
        for box, score, phrase in zip(boxes, logits, phrases):
            detections.append({
                'label': phrase,
                'confidence': float(score),
                'box': box.tolist(),
                'location': self._describe_location(box, image.shape)
            })
        
        return detections


class GroundingDINOHybridProvider(AIProvider):
    """GroundingDINO + Ollama combined"""
    
    def __init__(self):
        self.grounding_dino = GroundingDINOProvider()
        self.ollama = OllamaProvider()
    
    def describe_image(self, image_path, prompt, model, custom_query=None):
        # 1. Run GroundingDINO detection
        detections = self.grounding_dino.describe_image(
            image_path, 
            prompt, 
            "Comprehensive Detection (Auto)",
            custom_query
        )
        
        # 2. Format detection summary
        detection_summary = self._summarize_detections(detections)
        
        # 3. Enhance prompt for Ollama
        enhanced_prompt = f"""
        {prompt}
        
        Note: The following objects were detected in the image:
        {detection_summary}
        
        Please incorporate this information into your description.
        """
        
        # 4. Get description from Ollama
        description = self.ollama.describe_image(
            image_path,
            enhanced_prompt,
            model  # User's chosen Ollama model
        )
        
        return description
```

---

## 📊 Example Use Cases

### Use Case 1: Workplace Safety Inspection

**Query**: `"safety equipment . hard hat . safety vest . fire extinguisher . first aid kit . hazards . spills . damaged equipment"`

**Result**:
```
Safety Inspection Report:
✓ Safety equipment detected:
  - Hard hats: 2 (locations: top-left, center-right)
  - Safety vests: 1 (location: bottom-center)
  - Fire extinguisher: 1 (location: left wall)

⚠ Potential concerns:
  - Damaged equipment: 1 (location: bottom-left)
  - No first aid kit visible

Description: The warehouse shows basic safety compliance with hard hats and 
vests being worn by workers. A fire extinguisher is properly mounted on the 
left wall. However, one piece of equipment appears damaged and should be 
inspected. No first aid kit is visible in the frame.
```

### Use Case 2: Retail Inventory Check

**Query**: `"products . empty shelves . misplaced items . price tags . promotional signs"`

**Result**:
```
Inventory Check:
✓ Products: 47 items detected across 6 shelves
⚠ Empty shelves: 2 sections (aisle 3, upper right)
⚠ Misplaced items: 3 detected
✓ Price tags: Visible on most products
✓ Promotional signs: 2 detected

Description: The retail aisle is generally well-stocked with 47 visible 
products. Two sections show empty shelves that need restocking. Three items 
appear to be in the wrong locations. Pricing is clearly displayed, and 
promotional signage is present.
```

### Use Case 3: Traffic Analysis

**Query**: `"vehicles . cars . trucks . motorcycles . bicycles . pedestrians . traffic signs . traffic lights"`

**Result**:
```
Traffic Analysis:
- Vehicles detected: 12 total
  • Cars: 8
  • Trucks: 2
  • Motorcycles: 1
  • Bicycles: 1
- Pedestrians: 4
- Traffic signs: 3 (2 stop signs, 1 speed limit)
- Traffic lights: 2 (both showing red)

Description: The intersection shows moderate traffic with 12 vehicles present. 
Most are passenger cars, with 2 trucks and 1 motorcycle. A cyclist and 4 
pedestrians are visible. Traffic control includes 3 signs and 2 traffic lights, 
both currently red. All vehicles appear to be properly stopped.
```

---

## 🚀 Getting Started

### Installation

```bash
# Install GroundingDINO
pip install groundingdino-py

# Download model weights (auto-downloads on first use, ~700MB)
# Or manual download:
wget https://github.com/IDEA-Research/GroundingDINO/releases/download/v0.1.0-alpha/groundingdino_swint_ogc.pth
```

### Quick Test

```python
from groundingdino.util.inference import load_model, predict
from PIL import Image

# Load model
model = load_model()

# Load image
image = Image.open("test_image.jpg")

# Simple test
boxes, logits, phrases = predict(
    model=model,
    image=image,
    caption="objects . people . animals",
    box_threshold=0.35
)

print(f"Found {len(phrases)} objects:")
for phrase, score in zip(phrases, logits):
    print(f"  - {phrase}: {score:.2f}")
```

---

## 💡 Key Advantages Over YOLO

| Feature | YOLO | GroundingDINO |
|---------|------|---------------|
| **Classes** | 80 fixed | Unlimited (any text) |
| **Specificity** | Generic ("person") | Specific ("person wearing red hat") |
| **Attributes** | None | Yes ("red car", "large dog") |
| **Custom queries** | No | Yes |
| **Training needed** | Yes (for new classes) | No (zero-shot) |
| **Speed** | Very fast (~20ms) | Moderate (~200ms) |
| **Model size** | ~6-138MB | ~700MB |

---

## 🎯 Recommended Implementation

### Minimum Viable Product (MVP)

```python
class GroundingDINOProvider(AIProvider):
    """Just the basics - default comprehensive scan"""
    
    def describe_image(self, image_path, prompt, model):
        # Run with default broad prompt
        detections = self.detect("objects . people . animals . vehicles . furniture")
        
        # Format as simple list
        return self.format_detection_list(detections)
```

### Full Implementation

```python
# Multiple modes:
1. Default comprehensive scan
2. Category-specific presets (indoor/outdoor/safety)
3. Custom user queries
4. Hybrid with Ollama (detection + description)
5. Progressive refinement (initial → refined)
```

---

## 🔮 Future Enhancements

- **Visual feedback**: Draw bounding boxes on preview
- **Interactive selection**: Click detected objects to refine
- **Smart presets**: AI suggests relevant queries based on image
- **Batch queries**: Run multiple prompts simultaneously
- **Comparison mode**: "Find differences between images"
- **Temporal analysis**: "Objects added/removed since last time"

---

**Bottom Line**: GroundingDINO is **revolutionary** because it breaks the "80 classes" limitation. You can ask it to find **anything** you can describe in words. Combined with Ollama for descriptions, you get both precise detection AND natural language understanding. 🎯✨
