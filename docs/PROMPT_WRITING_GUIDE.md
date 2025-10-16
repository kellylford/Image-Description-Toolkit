# Prompt Writing Guide for Image-Description-Toolkit

**Version 2.0 | October 2025**

## Table of Contents
1. [Overview](#overview)
2. [Understanding Prompts vs Prompt Styles](#understanding-prompts-vs-prompt-styles)
3. [Built-In Prompt Styles](#built-in-prompt-styles)
4. [How Models Interpret Prompts](#how-models-interpret-prompts)
5. [Choosing the Right Prompt Style](#choosing-the-right-prompt-style)
6. [Model-Specific Considerations](#model-specific-considerations)
7. [Creating Custom Prompts](#creating-custom-prompts)
8. [Advanced Techniques](#advanced-techniques)
9. [Common Pitfalls](#common-pitfalls)
10. [Examples & Comparisons](#examples--comparisons)

---

## Overview

Image-Description-Toolkit supports multiple **prompt styles** that dramatically change how vision models describe images. Understanding these prompts and how different models respond to them is key to getting high-quality, purpose-fit descriptions.

### Key Concepts

- **Prompt Style**: A predefined instruction template that tells the model HOW to describe images
- **Prompt Template**: The actual text sent to the model
- **Model Interpretation**: How different models respond to the same prompt (varies significantly!)
- **Output Format**: The structure and style of the generated description

---

## Understanding Prompts vs Prompt Styles

### What is a Prompt Style?

A prompt style is a **named configuration** that selects a specific instruction template. Think of it as a "preset" that determines:

1. **What information to include** (objects, colors, mood, technical details, etc.)
2. **How to structure the output** (narrative, bullet points, sections, etc.)
3. **The level of detail** (concise, detailed, verbose, minimal)
4. **The perspective** (descriptive, artistic, technical, metadata-focused)

### How Prompts Work in IDT

```
User specifies:     --prompt-style detailed
                           ↓
IDT looks up:       image_describer_config.json
                           ↓
Finds template:     "Describe this image in detail, including:\n
                     - Main subjects/objects\n..."
                           ↓
Sends to model:     Vision model receives the template + image
                           ↓
Model generates:    Structured description following instructions
```

---

## Built-In Prompt Styles

IDT comes with **7 built-in prompt styles**, each optimized for different use cases.

### 1. **narrative** (Default)

**Prompt Text:**
```
Provide a narrative description including objects, colors and detail. 
Avoid interpretation, just describe.
```

**Best For:**
- General-purpose descriptions
- Alt text for accessibility
- Photo archives and personal collections
- When you want natural, flowing prose

**Output Characteristics:**
- Continuous narrative flow (no sections)
- 200-400 words typical
- Straightforward, objective description
- No markdown formatting
- Easy to read aloud

**Example Output:**
```
The image shows a corner of a room viewed from above, angled downward. 
The floor is covered in dark brown wood-look laminate planks with visible 
grain patterns and subtle variations in tone. Along the bottom left edge, 
a portion of a rug is visible, featuring a red border with intricate floral 
and vine motifs in beige, dark red, and green tones...
```

---

### 2. **detailed**

**Prompt Text:**
```
Describe this image in detail, including:
- Main subjects/objects
- Setting/environment
- Key colors and lighting
- Notable activities or composition
Keep it comprehensive and informative for metadata.
```

**Best For:**
- Digital Asset Management (DAM) systems
- Photo databases and catalogs
- Metadata-driven applications
- When you need structured, searchable descriptions
- Baseline testing and comparisons

**Output Characteristics:**
- **Structured sections** with markdown headers
- Uses `---` separators between sections
- 400-800 words typical
- Includes suggested metadata tags
- Predictable, parseable format

**Sections Generated:**
1. **Main Subjects/Objects** - What's in the image
2. **Setting/Environment** - Where and when
3. **Key Colors and Lighting** - Visual atmosphere
4. **Notable Activities or Composition** - Dynamic elements
5. **Metadata Tags (Suggested)** - Keywords for indexing

**Example Output:**
```
**Image Description for Metadata**

---

**Main Subjects/Objects:**

The central subject is a cascading waterfall flowing vertically down a 
rugged, moss-covered rock face. The water descends in a narrow, energetic 
stream, breaking into white froth as it tumbles over uneven ledges...

---

**Setting/Environment:**

The waterfall is situated in a natural, forested ravine or gully, likely 
in a tropical or subtropical region given the abundance of moisture-loving 
flora...

---

**Key Colors and Lighting:**

Dominant colors include deep greens from the foliage and moss, dark grays 
and blacks of the wet rock, and brilliant whites from the churning water...

---

**Notable Activities or Composition:**

The waterfall is the dynamic focal point, with motion conveyed through the 
blurred, frothy cascade...

---

**Metadata Tags (Suggested):**
- waterfall
- nature
- tropical forest
- landscape photography
```

---

### 3. **concise**

**Prompt Text:**
```
Describe this image concisely, including:
- Main subjects/objects
- Setting/environment
- Key colors and lighting
- Notable activities or composition.
```

**Best For:**
- Quick processing of large image sets
- Social media captions
- When storage/processing costs matter
- Overview descriptions without excessive detail

**Output Characteristics:**
- Shorter descriptions (100-200 words)
- Covers all essential elements
- Less verbose than detailed or narrative
- Efficient token usage

**Example Output:**
```
A group of approximately 20-25 adults pose indoors for a photo, many wearing 
Milwaukee Brewers baseball apparel. The setting appears to be a private suite 
at a stadium, with large windows showing the field behind them. Dominant colors 
are navy blue, white, and team colors. A table in the foreground holds snacks 
and beverages, suggesting a social gathering or fan event.
```

---

### 4. **artistic**

**Prompt Text:**
```
Analyze this image from an artistic perspective, describing:
- Visual composition and framing
- Color palette and lighting mood
- Artistic style or technique
- Emotional tone or atmosphere
- Subject matter and symbolism
```

**Best For:**
- Art collections and galleries
- Photography portfolios
- Creative projects
- When interpretation and mood matter
- Museum catalogs

**Output Characteristics:**
- Interpretive and analytical
- Discusses artistic techniques
- Addresses emotional impact
- May reference art movements/styles
- 300-500 words typical

**Example Output:**
```
The composition employs a dynamic diagonal thrust, with the waterfall creating 
a strong vertical axis that anchors the frame. The photographer has utilized a 
moderate shutter speed to capture the water's motion as a silky blur, contrasting 
beautifully with the sharp, textured detail of the surrounding foliage.

The color palette is dominated by deep, saturated greens that evoke the humid, 
primordial atmosphere of an undisturbed forest ecosystem. Punctuating this verdant 
backdrop, the brilliant white of the cascading water serves as a luminous focal 
point, drawing the eye inexorably downward...
```

---

### 5. **technical**

**Prompt Text:**
```
Provide a technical analysis of this image:
- Camera settings and photographic technique
- Lighting conditions and quality
- Composition and framing
- Image quality and clarity
- Technical strengths or weaknesses
```

**Best For:**
- Photography education
- Technical reviews
- Camera/lens testing
- Professional photography workflows
- Quality control

**Output Characteristics:**
- Focuses on technical aspects
- May infer camera settings
- Discusses photographic techniques
- Evaluates image quality
- 250-400 words typical

**Example Output:**
```
The image appears to have been captured with a moderate shutter speed 
(likely 1/15 to 1/4 second) to achieve the characteristic motion blur in 
the water while maintaining sharpness in the stationary elements. The 
photographer has likely used a narrow aperture (f/11 to f/16) to achieve 
the extended depth of field that keeps both foreground foliage and background 
rock face in acceptable focus.

The lighting is natural and diffused, suggesting either overcast conditions 
or a shaded ravine. This soft illumination minimizes harsh shadows and allows 
the camera to capture detail across a wide tonal range...
```

---

### 6. **colorful**

**Prompt Text:**
```
Give me a rich, vivid description emphasizing colors, lighting, and visual 
atmosphere. Focus on the palette, color relationships, and how colors contribute 
to the mood and composition.
```

**Best For:**
- Interior design documentation
- Fashion and product photography
- When color accuracy is critical
- Artistic color analysis
- Visual mood boards

**Output Characteristics:**
- Emphasizes color vocabulary
- Describes color relationships
- Focuses on visual atmosphere
- Rich, evocative language
- 200-400 words typical

**Example Output:**
```
The image is a symphony of deep, lush greens - from the bright, almost 
neon lime of sunlit moss to the dark, shadowy forest greens receding into 
the background. These verdant tones dominate the frame, creating an 
enveloping, immersive atmosphere of natural vitality.

Against this emerald backdrop, the waterfall appears as a cascade of pure 
white and pale blue-gray, its churning surface catching and reflecting 
ambient light. Where the water strikes the dark basalt rocks below, it 
froths into brilliant white foam, creating a stark, high-contrast focal 
point that draws the eye...
```

---

### 7. **Simple**

**Prompt Text:**
```
Describe.
```

**Best For:**
- Minimal token usage
- Testing model baseline behavior
- When you want unbiased, natural output
- Experimentation

**Output Characteristics:**
- Completely model-dependent
- Usually brief (50-150 words)
- No structure enforced
- Models use their default behavior
- Unpredictable format

**Example Output:**
```
A waterfall in a forest.
```
*(Output varies dramatically by model - some may provide more detail, others less)*

---

## How Models Interpret Prompts

Different vision models respond to the same prompt in dramatically different ways. Understanding these differences helps you choose the right model for your needs.

### Structured vs Unstructured Output

**Models That Generate Structured Output (with detailed prompt):**
- ✅ **qwen3-vl (all sizes)** - Excellent markdown structure, consistent sections
- ✅ **llama3.2-vision** - Good structure, follows bullet points
- ✅ **GPT-4o / GPT-4o-mini** - Professional structure, comprehensive
- ✅ **Claude Opus/Sonnet 4.x** - Highly structured, markdown-aware
- ⚠️ **minicpm-v** - Partial structure, less consistent

**Models That Generate Narrative Output (even with detailed prompt):**
- ❌ **llava (most versions)** - Tends toward flowing narrative regardless of prompt
- ❌ **moondream** - Simple, straightforward descriptions
- ❌ **bakllava** - Narrative focus, minimal structure

### Prompt Compliance by Model

**Highest Compliance (follows prompts precisely):**
1. **Claude Opus 4.1** - Nearly perfect instruction following
2. **GPT-4o** - Excellent compliance, professional output
3. **qwen3-vl:235b-cloud** - Outstanding structure and detail
4. **llama3.2-vision:11b** - Very good compliance

**Medium Compliance:**
5. **llama3.2-vision:3b** - Good but sometimes simplified
6. **llava:13b** - Reasonable compliance
7. **minicpm-v:8b** - Variable compliance

**Lower Compliance (more creative interpretation):**
8. **moondream** - Simple descriptions, ignores structure
9. **llava:7b** - Basic descriptions
10. **bakllava** - Narrative-focused

### Token Usage Differences

Approximate tokens per image description:

| Model | Concise | Narrative | Detailed |
|-------|---------|-----------|----------|
| **qwen3-vl:235b** | 150-250 | 300-500 | 600-1000 |
| **GPT-4o** | 100-200 | 200-400 | 500-800 |
| **Claude Opus 4.1** | 150-300 | 300-600 | 700-1200 |
| **llama3.2-vision:11b** | 100-180 | 200-350 | 400-700 |
| **llava:13b** | 80-150 | 150-300 | 250-500 |
| **moondream** | 50-100 | 80-150 | 100-200 |

*Note: Detailed prompts can generate 2-3x more tokens than concise prompts*

---

## Choosing the Right Prompt Style

Use this decision tree to select the optimal prompt style:

### By Use Case

```
Personal photo archive → narrative
Digital asset management → detailed  
Alt text for web → narrative or concise
Art gallery catalog → artistic
Photography review → technical
Interior design docs → colorful
Social media captions → concise or colorful
Database/search → detailed
Education/training → technical or artistic
Quick processing → Simple or concise
```

### By Priority

**When STRUCTURE matters most:**
→ Use `detailed` with structured models (qwen3-vl, GPT-4o, Claude)

**When COST matters most:**
→ Use `Simple` or `concise` with local models (moondream, llava)

**When ACCESSIBILITY matters most:**
→ Use `narrative` (flows naturally when read aloud)

**When SEARCHABILITY matters most:**
→ Use `detailed` (generates metadata tags)

**When ARTISTIC VALUE matters most:**
→ Use `artistic` (interprets mood and technique)

**When COLOR ACCURACY matters most:**
→ Use `colorful` (emphasizes palette and relationships)

### By Model Capability

**For Cloud Models (GPT-4o, Claude):**
- `detailed` - Takes full advantage of structure capability
- `artistic` or `technical` - Advanced analysis
- `narrative` - Professional, flowing prose

**For Large Local Models (qwen3-vl:235b, llama3.2-vision:11b):**
- `detailed` - Excellent structured output
- Any style works well
- Balance quality vs speed/cost

**For Medium Local Models (llava:13b, minicpm-v:8b):**
- `narrative` - Natural strength
- `concise` - Efficient processing
- Avoid overly complex prompts

**For Small Local Models (moondream, llava:7b):**
- `Simple` or `narrative` - Play to strengths
- `concise` - Reasonable quality
- Avoid `detailed` or `technical` (won't follow structure)

---

## Model-Specific Considerations

### Ollama Local Models

#### **qwen3-vl:235b-cloud** (RECOMMENDED)
- **Size:** ~140GB
- **Best prompts:** detailed, artistic, technical
- **Strengths:** Exceptional structure, follows instructions precisely, generates professional metadata
- **Weaknesses:** Requires cloud/powerful hardware, slower processing
- **Speed:** ~10-15 seconds/image
- **Cost:** Free (local), but high memory requirements

#### **llama3.2-vision:11b**
- **Size:** ~7.9GB
- **Best prompts:** detailed, narrative, concise
- **Strengths:** Good balance of quality and speed, reliable structure
- **Weaknesses:** Less detailed than qwen3-vl
- **Speed:** ~3-5 seconds/image
- **Cost:** Free (local)

#### **llama3.2-vision:3b**
- **Size:** ~2GB
- **Best prompts:** narrative, concise
- **Strengths:** Fast, efficient, good for large batches
- **Weaknesses:** Less detail, simpler vocabulary
- **Speed:** ~1-2 seconds/image
- **Cost:** Free (local)

#### **llava:13b**
- **Size:** ~8GB
- **Best prompts:** narrative, concise
- **Strengths:** Solid descriptions, narrative flow
- **Weaknesses:** Doesn't follow structure well
- **Speed:** ~3-5 seconds/image
- **Cost:** Free (local)

#### **llava:7b**
- **Size:** ~4.7GB
- **Best prompts:** Simple, narrative
- **Strengths:** Fast, lightweight, decent quality
- **Weaknesses:** Basic descriptions only
- **Speed:** ~2-3 seconds/image
- **Cost:** Free (local)

#### **moondream**
- **Size:** ~1.6GB
- **Best prompts:** Simple, narrative
- **Strengths:** Extremely fast, tiny size, good for quick processing
- **Weaknesses:** Very basic descriptions, ignores complex prompts
- **Speed:** ~0.5-1 second/image
- **Cost:** Free (local)

#### **bakllava**
- **Size:** ~4.4GB
- **Best prompts:** narrative, Simple
- **Strengths:** Good narrative descriptions
- **Weaknesses:** Ignores structure, narrative-only
- **Speed:** ~2-4 seconds/image
- **Cost:** Free (local)

#### **minicpm-v:8b**
- **Size:** ~5.5GB
- **Best prompts:** narrative, concise
- **Strengths:** Compact, efficient, reasonable quality
- **Weaknesses:** Variable compliance with prompts
- **Speed:** ~2-4 seconds/image
- **Cost:** Free (local)

#### **qwen2-vl:7b** and **qwen2-vl:2b**
- **Size:** ~4.6GB / ~1.5GB
- **Best prompts:** narrative, concise
- **Strengths:** Good qwen family quality in smaller size
- **Weaknesses:** Less capable than qwen3-vl:235b
- **Speed:** ~2-3 / ~1-2 seconds/image
- **Cost:** Free (local)

### Cloud Models (OpenAI)

#### **GPT-4o**
- **Best prompts:** detailed, artistic, technical
- **Strengths:** Exceptional quality, perfect structure, comprehensive detail
- **Weaknesses:** Expensive
- **Speed:** ~2-5 seconds/image
- **Cost:** ~$0.50-2.00 per 100 images (Oct 2025 pricing)

#### **GPT-4o-mini**
- **Best prompts:** detailed, narrative, concise
- **Strengths:** Good quality, much cheaper than GPT-4o
- **Weaknesses:** Less detailed than full GPT-4o
- **Speed:** ~1-3 seconds/image
- **Cost:** ~$0.05-0.20 per 100 images (Oct 2025 pricing)

### Cloud Models (Anthropic Claude)

#### **Claude Opus 4.1**
- **Best prompts:** detailed, artistic, technical
- **Strengths:** Best-in-class quality, incredible detail, perfect instruction following
- **Weaknesses:** Most expensive option
- **Speed:** ~2-6 seconds/image
- **Cost:** ~$3.00-6.00 per 100 images (Oct 2025 pricing)

#### **Claude Sonnet 4.5**
- **Best prompts:** detailed, narrative, artistic
- **Strengths:** Excellent quality/cost balance, very reliable
- **Weaknesses:** Slightly less detail than Opus
- **Speed:** ~1-4 seconds/image
- **Cost:** ~$0.50-1.50 per 100 images (Oct 2025 pricing)

#### **Claude Haiku 3.5**
- **Best prompts:** narrative, concise
- **Strengths:** Fast, economical, good quality
- **Weaknesses:** Less comprehensive than Opus/Sonnet
- **Speed:** ~1-2 seconds/image
- **Cost:** ~$0.10-0.40 per 100 images (Oct 2025 pricing)

---

## Creating Custom Prompts

You can create custom prompt styles by editing `scripts/image_describer_config.json`.

### Adding a New Prompt Style

1. Open `scripts/image_describer_config.json`
2. Locate the `"prompt_variations"` section
3. Add your custom prompt:

```json
{
  "prompt_variations": {
    "detailed": "...",
    "narrative": "...",
    "my_custom_prompt": "Your custom instruction text here. Be specific about what you want the model to describe and how to format the output."
  }
}
```

4. Use it with: `idt workflow --prompt-style my_custom_prompt`

### Custom Prompt Best Practices

**DO:**
- ✅ Be specific about what to include
- ✅ Specify desired output structure if needed
- ✅ Use clear, unambiguous language
- ✅ Test with multiple models
- ✅ Start with bullet points for structured output
- ✅ Mention the purpose (e.g., "for metadata", "for accessibility")

**DON'T:**
- ❌ Make prompts overly long (>200 words)
- ❌ Use vague instructions like "be creative"
- ❌ Assume all models will follow structure
- ❌ Contradict yourself (e.g., "be concise" then ask for "comprehensive detail")
- ❌ Use model-specific terminology

### Example Custom Prompts

**For E-commerce Product Descriptions:**
```json
"product": "Describe this product image for an online store listing. Include: product name/type, key features, colors, materials, condition, and any text visible on the product. Focus on details a buyer would need to make a purchase decision."
```

**For Historical Photo Archives:**
```json
"historical": "Describe this historical photograph with attention to: time period indicators (clothing, vehicles, architecture), people (number, activities, demographics visible), location details, and any text or signage. Maintain objectivity and avoid speculation about context not visible in the image."
```

**For Medical/Scientific Imaging:**
```json
"scientific": "Provide a factual, objective description of this scientific/medical image. Include: specimen or subject type, visible structures or features, scale indicators, labeling or annotations, imaging technique (if evident), and notable characteristics. Use appropriate technical terminology."
```

**For Real Estate:**
```json
"real_estate": "Describe this property image emphasizing: room type, size perception, condition, style/finishes, lighting (natural/artificial), furnishings (if any), special features, and overall appeal. Use language that highlights positive aspects while remaining accurate."
```

---

## Advanced Techniques

### Prompt Chaining

Process images multiple times with different prompts to get multifaceted descriptions:

```bash
# First pass: technical analysis
idt workflow images/ --prompt-style technical --name analysis_tech

# Second pass: artistic interpretation  
idt workflow images/ --prompt-style artistic --name analysis_art

# Third pass: metadata generation
idt workflow images/ --prompt-style detailed --name analysis_meta

# Combine results using analysis tools
python analysis/combine_workflow_descriptions.py Descriptions/
```

### Model Ensembling

Use multiple models with the same prompt to get consensus or diverse perspectives:

```bash
# Run same images through different models
bat/run_ollama_llama32vision11b.bat images/ --prompt-style detailed --name ensemble_llama
bat/run_openai_gpt4o_mini.bat images/ --prompt-style detailed --name ensemble_gpt
bat/run_claude_sonnet45.bat images/ --prompt-style detailed --name ensemble_claude

# Compare outputs
python analysis/combine_workflow_descriptions.py Descriptions/
```

### Conditional Prompting

Use different prompts based on image content (requires manual categorization or pre-processing):

```bash
# For landscape photos
idt workflow landscapes/ --prompt-style colorful --name landscapes

# For portraits
idt workflow portraits/ --prompt-style detailed --name portraits

# For technical diagrams
idt workflow diagrams/ --prompt-style technical --name diagrams
```

### Prompt Tuning for Specific Models

Some models respond better to certain phrasing:

**For moondream (keep it simple):**
```json
"moondream_optimized": "Describe what you see in this image."
```

**For qwen3-vl (use structure):**
```json
"qwen_optimized": "Provide a comprehensive image description with these sections:\n1. Main subjects\n2. Environment\n3. Colors and lighting\n4. Composition\n5. Notable details"
```

**For Claude (be precise):**
```json
"claude_optimized": "Analyze this image systematically, describing: visual elements, spatial relationships, color palette, lighting characteristics, compositional techniques, and contextual details. Structure your response with clear sections."
```

---

## Common Pitfalls

### Pitfall 1: Using Complex Prompts with Simple Models

**Problem:** Using `detailed` prompt with `moondream` or `llava:7b`

**Why it fails:** Small models don't have the capacity to follow complex structured prompts. They'll ignore the structure and generate simple descriptions anyway.

**Solution:** Match prompt complexity to model capability. Use `Simple` or `narrative` with smaller models.

### Pitfall 2: Expecting Consistent Structure from All Models

**Problem:** Assuming all models will generate markdown sections with the `detailed` prompt

**Why it fails:** Only certain models (qwen3-vl, GPT-4o, Claude) generate structured output. Most local models produce narrative text regardless of prompt.

**Solution:** Check model-specific documentation. Use appropriate analysis tools that handle both structured and narrative formats (like our fixed `combine_workflow_descriptions.py`).

### Pitfall 3: Not Testing Prompts Before Large Batches

**Problem:** Running 10,000 images with an untested custom prompt

**Why it fails:** You might discover output isn't what you expected after hours of processing.

**Solution:** Always test new prompts on 5-10 sample images first. Review output quality before scaling up.

### Pitfall 4: Mixing Prompts Without Purpose

**Problem:** Randomly using different prompts on the same image set

**Why it fails:** Makes analysis inconsistent and comparisons difficult.

**Solution:** Use consistent prompts for comparable datasets. Only mix prompts intentionally (e.g., for baseline testing or multi-perspective analysis).

### Pitfall 5: Ignoring Token Costs

**Problem:** Using `detailed` prompt with Claude Opus on 100,000 images

**Why it fails:** The `detailed` prompt generates 600-1200 tokens per image. At October 2025 pricing, this could cost $3000-6000.

**Solution:** 
- Use `concise` or `narrative` for large batches
- Use local models (qwen3-vl, llama3.2) when possible
- Reserve expensive cloud models for critical images
- Monitor costs with `idt stats` command

### Pitfall 6: Outdated Executables

**Problem:** Using old `idt.exe` that doesn't properly handle new prompt features

**Why it fails:** Code changes aren't reflected in frozen executables until rebuilt.

**Solution:** Rebuild executables after code changes:
```bash
cd /c/Users/kelly/GitHub/Image-Description-Toolkit
./build_idt.bat
cp dist/idt/idt.exe /c/idt/
```

---

## Examples & Comparisons

### Same Image, Different Prompts

**Image:** Waterfall in tropical forest

#### Simple Prompt Output:
```
A waterfall cascading down rocks in a lush forest.
```
*(21 words, ~30 tokens)*

#### Narrative Prompt Output:
```
The image shows a cascading waterfall flowing vertically down a rugged, moss-covered 
rock face. The water descends in a narrow, energetic stream, breaking into white froth 
as it tumbles over uneven ledges and pools at the base. Surrounding the waterfall are 
dense, lush green vegetation including ferns, mosses, and broadleaf plants clinging to 
the cliffside. In the foreground, branches with light-green leaves partially frame the 
scene from the right, adding depth and a sense of immersion. The rock face is dark, 
possibly volcanic or basaltic, with visible stratification and crevices. The environment 
appears humid and shaded, with sunlight filtering through the canopy above.
```
*(115 words, ~180 tokens)*

#### Detailed Prompt Output:
```
**Image Description for Metadata**

---

**Main Subjects/Objects:**

The central subject is a cascading waterfall flowing vertically down a rugged, moss-covered 
rock face. The water descends in a narrow, energetic stream, breaking into white froth as it 
tumbles over uneven ledges and pools at the base. Surrounding the waterfall are dense, lush 
green vegetation including ferns, mosses, and broadleaf plants clinging to the cliffside...

---

**Setting/Environment:**

The waterfall is situated in a natural, forested ravine or gully, likely in a tropical or 
subtropical region given the abundance of moisture-loving flora. The rock face is dark, 
possibly volcanic or basaltic, with visible stratification and crevices...

---

**Key Colors and Lighting:**

Dominant colors include deep greens from the foliage and moss, dark grays and blacks of the 
wet rock, and brilliant whites from the churning water. Sunlight illuminates parts of the 
scene—particularly the upper right foliage and the mid-section of the waterfall...

---

**Notable Activities or Composition:**

The waterfall is the dynamic focal point, with motion conveyed through the blurred, frothy 
cascade and splashing at the base. The composition is vertically oriented, emphasizing the 
height and descent of the water...

---

**Metadata Tags (Suggested):**
- waterfall
- tropical forest
- nature photography
- landscape
- water feature
- moss-covered rocks
- lush vegetation
```
*(~450 words, ~700 tokens)*

#### Artistic Prompt Output:
```
This image exemplifies the romantic sublime in nature photography, capturing the raw power 
and beauty of an untamed waterfall cascading through a primordial forest setting. The 
photographer has skillfully employed a vertical composition that emphasizes the dramatic 
descent of water, creating a strong visual axis that draws the viewer's eye inexorably 
downward through the frame.

The color palette is dominated by rich, saturated greens that evoke the humid, fecund 
atmosphere of a tropical or subtropical forest ecosystem. These verdant tones range from 
the bright, almost luminous lime of sun-struck moss to the deep, shadowy forest greens 
receding into the background, creating a sense of atmospheric depth...
```
*(~350 words, ~550 tokens)*

#### Technical Prompt Output:
```
The image appears to have been captured with a moderate shutter speed, likely between 1/15 
and 1/4 second, to achieve the characteristic silky blur in the waterfall while maintaining 
acceptable sharpness in the surrounding foliage. The photographer has employed a narrow 
aperture, probably f/11 to f/16, to maximize depth of field and keep both foreground 
elements and background rock face in focus.

The lighting conditions appear to be natural and diffused, suggesting either overcast weather 
or a shaded ravine environment. This soft illumination has allowed the camera to capture 
detail across a wide tonal range without blown highlights in the white water or blocked 
shadows in the darker rocks...
```
*(~280 words, ~450 tokens)*

#### Colorful Prompt Output:
```
The image is a symphony of deep, lush greens - from the bright, almost neon lime of sunlit 
moss to the dark, shadowy forest greens receding into the background. These verdant tones 
dominate the frame, creating an enveloping, immersive atmosphere of natural vitality.

Against this emerald backdrop, the waterfall appears as a cascade of pure white and pale 
blue-gray, its churning surface catching and reflecting ambient light. Where the water 
strikes the dark basalt rocks below, it froths into brilliant white foam, creating a stark, 
high-contrast focal point that draws the eye...
```
*(~250 words, ~400 tokens)*

---

## Quick Reference

### Prompt Style Selector

```
Need metadata? → detailed
Need accessibility? → narrative
Need speed? → Simple or concise
Need art analysis? → artistic
Need tech review? → technical
Need color focus? → colorful
Need balance? → narrative
```

### Model Selector by Budget

**Free (Local):**
- Best: qwen3-vl:235b-cloud
- Fast: llama3.2-vision:11b
- Efficient: moondream

**Budget ($):**
- GPT-4o-mini
- Claude Haiku 3.5

**Premium ($$$):**
- Claude Opus 4.1
- GPT-4o

### Token/Cost Estimator

Estimated costs for 1000 images (October 2025 pricing):

| Model | Simple | Narrative | Detailed |
|-------|--------|-----------|----------|
| **Local (all)** | $0 | $0 | $0 |
| **GPT-4o-mini** | $1-2 | $2-4 | $5-10 |
| **GPT-4o** | $10-15 | $15-25 | $40-60 |
| **Claude Haiku 3.5** | $1-3 | $3-6 | $8-15 |
| **Claude Sonnet 4.5** | $5-10 | $10-20 | $30-50 |
| **Claude Opus 4.1** | $20-40 | $40-80 | $120-200 |

*Note: Actual costs vary based on image complexity and output verbosity*

---

## Conclusion

Understanding prompts and models is essential for effective use of Image-Description-Toolkit:

1. **Match prompts to use cases** - Don't use `detailed` when `narrative` suffices
2. **Match prompts to models** - Complex prompts need capable models
3. **Test before scaling** - Always validate on sample images
4. **Monitor costs** - Use `idt stats` to track token usage
5. **Iterate and refine** - Custom prompts often need tuning

The built-in prompts cover most use cases, but don't hesitate to create custom prompts for specialized needs. The key is understanding how different models interpret your instructions and adjusting accordingly.

Happy describing! 🎨📸

---

**Document Version:** 1.0  
**Last Updated:** October 15, 2025  
**IDT Version:** 2.0+  
**Author:** Image-Description-Toolkit Team
