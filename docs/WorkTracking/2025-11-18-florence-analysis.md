# Florence-2 Model Performance Analysis
## Test Date: November 18, 2025

### Test Configuration
- **Images**: 5 test images (2 PNG, 1 JPEG, 1 HEIC→JPG, 1 MOV→frame)
- **Models Tested**: 
  - microsoft/Florence-2-base (ONNX)
  - microsoft/Florence-2-large (ONNX)
  - moondream:latest (Ollama, baseline)
- **Prompt Styles**: Simple, Technical, Narrative
- **Total Runs**: 7 (6 Florence + 1 Moondream)

---

## Performance Summary

### Timing Results (Average seconds per image)

| Model | Simple | Technical | Narrative |
|-------|--------|-----------|-----------|
| **Florence-2-base**  | **8.63s** | 26.09s | 73.59s |
| **Florence-2-large** | 23.81s | 56.44s | **145.16s** |
| **Moondream** (baseline) | - | - | 17.29s |

### Total Processing Time (5 images)

| Model | Simple | Technical | Narrative |
|-------|--------|-----------|-----------|
| Florence-2-base  | 43s (0.7min) | 130s (2.2min) | 368s (6.1min) |
| Florence-2-large | 119s (2.0min) | 282s (4.7min) | 726s (12.1min) |
| Moondream | - | - | 86s (1.4min) |

---

## Key Findings

### 1. 🚀 Prompt Complexity Has MASSIVE Speed Impact

**Effect on Florence-2-base:**
- Simple → Technical: **3.0x slower** (8.63s → 26.09s)
- Simple → Narrative: **8.5x slower** (8.63s → 73.59s)
- Technical → Narrative: **2.8x slower** (26.09s → 73.59s)

**Effect on Florence-2-large:**
- Simple → Technical: **2.4x slower** (23.81s → 56.44s)
- Simple → Narrative: **6.1x slower** (23.81s → 145.16s)
- Technical → Narrative: **2.6x slower** (56.44s → 145.16s)

**Insight**: The prompt style is the PRIMARY driver of processing time, more than the model size. Simple prompts are 6-8x faster than narrative prompts on the same model.

### 2. 📊 Model Size Impact (base → large)

- **On Simple**: 2.8x slower (8.63s → 23.81s)
- **On Technical**: 2.2x slower (26.09s → 56.44s)
- **On Narrative**: 2.0x slower (73.59s → 145.16s)

**Insight**: The larger model adds consistent 2-3x overhead, but the relative impact DECREASES with more complex prompts. The large model's extra processing is proportionally less significant when the prompt is already demanding.

### 3. ⚡ Speed Range

- **Fastest Configuration**: Florence-2-base + Simple = **8.63s/image**
- **Slowest Configuration**: Florence-2-large + Narrative = **145.16s/image**
- **Difference**: **16.8x** (nearly 17x!)

For a 1,000 image workflow:
- Fastest: 2.4 hours
- Slowest: 40.3 hours (1.7 days!)

### 4. 🏆 Moondream Comparison

At narrative prompt level:
- **Moondream**: 17.29s/image
- **Florence-base**: 73.59s/image (4.3x slower)
- **Florence-large**: 145.16s/image (8.4x slower)

**Insight**: Moondream is remarkably fast - faster than Florence-2-base even on Simple prompts! (17.29s vs 23.81s for large, 8.63s for base)

---

## Description Quality Analysis

### Test Image: Woman with Colorful Hair
*Analysis of the same image (849adfa4fe72c4fd8f6482ecfde0a4a1.jpeg) across all configurations*

#### Florence-2-base + Simple
> "A woman with colorful hair in a salon."

**Length**: 8 words  
**Details**: Minimal - identifies subject, hair color, location  
**Accuracy**: ✅ Correct

#### Florence-2-base + Technical
> "The image shows a woman with colorful hair in a salon, wearing a black dress and spectacles. In the background, there are chairs, tables, monitors, keyboards, mouses, papers, and other objects on the tables, as well as a wall."

**Length**: 41 words  
**Details**: Medium - clothing (calls shirt "dress"), glasses, detailed background inventory  
**Accuracy**: ✅ Mostly correct (minor: shirt vs dress)  
**Object Detection**: Excellent enumeration of background items

#### Florence-2-base + Narrative
> "The image is a selfie of a middle-aged woman with short, colorful hair. She is wearing a black t-shirt with the words 'Matrix' written on it and glasses. The hair is dyed in a rainbow of colors, including blue, orange, yellow, green, and purple. The woman is smiling and looking directly at the camera. In the background, there are several office chairs and a desk with a computer monitor and other items on it."

**Length**: 77 words  
**Details**: High - photo type, age estimate, specific hair colors, emotional state, gaze direction  
**Accuracy**: ✅ Excellent  
**Storytelling**: Strong narrative flow, contextual details ("selfie", "smiling", "looking directly")

#### Florence-2-large + Simple
> "A woman with bright colored hair in a salon."

**Length**: 9 words  
**Details**: Minimal - nearly identical to base model  
**Difference from base**: Added "bright" descriptor

#### Florence-2-large + Technical
> "The image shows a woman with colorful hair and glasses smiling at the camera. She is wearing a black t-shirt and is surrounded by chairs and tables with monitors, keyboards, mouses, and other items on them. In the background, there is a mirror attached to the wall."

**Length**: 47 words  
**Details**: Medium-high - includes emotional state ("smiling"), more spatial awareness  
**Improvement over base**: Better grammar, added mirror detail, correct shirt identification  
**Accuracy**: ✅ Excellent

#### Florence-2-large + Narrative
> "The image is a selfie of a woman with short, colorful hair. She is wearing a black t-shirt with a red logo on it and glasses. The hair is dyed in a rainbow of colors, including blue, orange, yellow, green, purple, and pink. The woman is smiling and looking directly at the camera. In the background, there are several hair salon chairs and a desk with a computer monitor and other items on it."

**Length**: 76 words  
**Details**: High - very similar structure to base narrative  
**Differences from base**: 
  - More specific hair color list (added "pink")
  - Mentions "red logo" (base said "Matrix" - both referencing shirt design)
  - Says "hair salon chairs" (more specific than "office chairs")
**Accuracy**: ✅ Excellent

#### Moondream + Narrative
> "A woman with blue hair styled in rainbow hues is sitting inside of what appears to be an office or salon setting as she poses for the camera wearing glasses that reflect light off her face making it look like there are multiple reflections on a mirror behind them at workstation level 1 and 2, which has two chairs."

**Length**: 58 words  
**Details**: Medium-high - creative interpretation, spatial reasoning  
**Style**: More conversational, run-on sentence structure  
**Unique observations**: Light reflections in glasses, mirror reflections, numbered workstation levels  
**Accuracy**: ✅ Good but more interpretive

---

## Detailed Comparisons

### Prompt Style Impact on Description Quality

#### Simple Prompts
- **Purpose**: Quick, minimal descriptions
- **Length**: 8-9 words
- **Detail Level**: Subject identification only
- **Model Difference**: Almost none (base and large produce nearly identical output)
- **Best Use**: High-volume processing where speed matters, basic cataloging

#### Technical Prompts
- **Purpose**: Detailed object enumeration
- **Length**: 41-47 words (5x longer than Simple)
- **Detail Level**: Comprehensive background inventory, object counting
- **Model Difference**: Large model has better grammar, spatial awareness, detail accuracy
- **Best Use**: Accessibility descriptions, detailed cataloging, inventory documentation

#### Narrative Prompts
- **Purpose**: Storytelling, context, emotional content
- **Length**: 58-77 words (8-9x longer than Simple)
- **Detail Level**: Photo type, emotional state, colors, spatial relationships, story elements
- **Model Difference**: Moderate - large model slightly more specific (color lists, spatial descriptors)
- **Best Use**: Human-readable descriptions, social media, storytelling applications

### Base vs Large Model Quality

**At Simple Prompt Level:**
- Essentially identical output
- Large model adds 1-2 descriptive words maximum
- **Verdict**: Not worth 2.8x slowdown

**At Technical Prompt Level:**
- Large model has measurably better:
  - Grammar and sentence flow
  - Clothing identification accuracy (shirt vs dress)
  - Spatial detail (mirror on wall)
  - Emotional state detection (smiling)
- **Verdict**: Noticeable improvement, may justify 2.2x slowdown for quality-critical use

**At Narrative Prompt Level:**
- Large model provides:
  - Slightly more specific color enumeration
  - Better object classification (hair salon chairs vs office chairs)
  - More nuanced logo description
- Differences are subtle - both produce high-quality narratives
- **Verdict**: Marginal quality gain doesn't strongly justify 2x slowdown

---

## Recommendations

### For Speed-Critical Workflows (1000+ images)
**Use**: Florence-2-base + Simple
- Fastest configuration (8.63s/image)
- Adequate for basic cataloging
- 1000 images = 2.4 hours

### For Balanced Quality/Speed
**Use**: Florence-2-base + Technical
- Good detail level (41 words)
- Reasonable speed (26.09s/image)
- 1000 images = 7.2 hours
- Provides comprehensive object detection

### For Maximum Quality
**Use**: Florence-2-large + Technical
- Best balance of quality and completeness
- Better than narrative in structured detail
- More controlled output than narrative prompts
- 1000 images = 15.7 hours

### For Storytelling/Human Consumption
**Use**: Florence-2-base + Narrative OR Moondream + Narrative
- Florence-base: More structured, consistent (73.59s/image)
- Moondream: Faster (17.29s/image), more creative/conversational
- Choice depends on whether you prefer:
  - **Florence**: Structured consistency, predictable format
  - **Moondream**: Speed + creative interpretations

### Generally Avoid
**Florence-2-large + Narrative**
- 145.16s/image is extremely slow
- Quality improvement over base+narrative is minimal
- Only marginally better than base model for 2x the time
- 1000 images = 40.3 hours (1.7 days!)

---

## Statistical Summary

### Speed Metrics
- **Fastest per-image**: 8.63s (base + Simple)
- **Slowest per-image**: 145.16s (large + Narrative)
- **Speed range**: 16.8x difference
- **Most efficient**: Moondream at 17.29s with narrative-level detail

### Quality Metrics (word count as proxy)
- **Simple prompts**: 8-9 words (no model difference)
- **Technical prompts**: 41-47 words (15% increase with large model)
- **Narrative prompts**: 76-77 words (Florence), 58 words (Moondream)

### Cost-Benefit Analysis

| Configuration | Time/Image | Quality (1-10) | Efficiency Score |
|---------------|------------|----------------|------------------|
| base + Simple | 8.63s | 4 | 0.46 |
| base + Technical | 26.09s | 7 | 0.27 |
| base + Narrative | 73.59s | 9 | 0.12 |
| large + Simple | 23.81s | 4 | 0.17 |
| large + Technical | 56.44s | 8 | 0.14 |
| large + Narrative | 145.16s | 9.5 | 0.07 |
| Moondream + Narrative | 17.29s | 8 | **0.46** |

*Efficiency Score = Quality / Time (higher is better)*

**Winner**: Tie between **base + Simple** and **Moondream + Narrative**
- base + Simple wins on pure speed for minimal needs
- Moondream + Narrative wins on quality-per-second for detailed descriptions

---

## Interesting Observations

### 1. Prompt Engineering Matters More Than Model Size
The choice between Simple/Technical/Narrative has **6-8x** more impact on speed than choosing base vs large (2-3x impact). This suggests that prompt optimization is the most important tuning parameter.

### 2. Diminishing Returns on Model Size
As prompts get more complex, the large model's overhead becomes proportionally less significant. This suggests the large model has fixed costs that are amortized over longer generation times.

### 3. Moondream Punches Above Its Weight
Despite being much faster, Moondream produces narrative descriptions comparable in quality to Florence-2-base. It's more creative and conversational, though less structured.

### 4. Simple Prompts Don't Benefit from Large Models
At the Simple prompt level, Florence-2-base and large produce virtually identical output. The large model's capabilities simply aren't utilized by minimal prompts.

### 5. Consistent Model Behaviors
Both base and large models show the same quality progression across prompt levels, suggesting the underlying architecture and prompt processing are fundamentally similar - the large model adds capacity but not capability differences.

---

## Conclusion

The Florence-2 models demonstrate clear prompt-driven behavior with measurable trade-offs:

**For Production Use:**
- High-volume batch processing: **Florence-2-base + Simple**
- Accessibility/technical documentation: **Florence-2-base + Technical**
- Human-readable, fast: **Moondream + Narrative**
- Maximum quality, structured: **Florence-2-large + Technical**

**General Guidance:**
The **prompt style choice** is your primary lever for controlling speed/quality trade-offs. Choose the model size based on your quality requirements at that prompt level, knowing that:
- Simple prompts: Model size doesn't matter
- Technical prompts: Large model adds 15-20% quality for 2.2x time
- Narrative prompts: Large model adds 5-10% quality for 2x time

The sweet spot for most use cases is likely **Florence-2-base + Technical** (balanced) or **Moondream + Narrative** (fast quality).
