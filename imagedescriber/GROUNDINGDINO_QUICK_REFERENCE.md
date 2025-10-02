# GroundingDINO - Quick Reference Card

## 🚀 Installation (One-Time)

**Run:** `install_groundingdino.bat`

**Or manually:**
```bash
pip install groundingdino-py torch torchvision
```

**Test installation:** `test_groundingdino.bat`

---

## 📦 Model Download (Automatic)

- **Size:** ~700MB
- **When:** Automatically on first use
- **Where:** `C:\Users\<You>\.cache\groundingdino\`
- **Time:** 2-10 minutes (internet dependent)
- **After:** Works offline, instant startup

---

## 🎯 Using in ImageDescriber

### Basic Detection

1. **Select image** in workspace
2. **Process Image** → Choose provider:
   - **GroundingDINO** (detection only)
   - **GroundingDINO + Ollama** (detection + descriptions)
3. **Configure detection**:
   - **Automatic mode**: Select preset
   - **Custom mode**: Type your query
4. **Adjust confidence** (default 25%)
5. **Click OK**

### Automatic Mode Presets

| Preset | What It Detects |
|--------|----------------|
| **Comprehensive** | General objects, people, vehicles, furniture, electronics, nature |
| **Indoor** | People, furniture, electronics, decorations, appliances |
| **Outdoor** | People, vehicles, buildings, trees, roads, signs, nature |
| **Workplace** | People, computers, equipment, safety gear, tools, machinery |
| **Safety** | Fire extinguishers, exits, safety equipment, hazards, warning signs |
| **Retail** | Products, shelves, people, displays, signage, prices |
| **Document** | Text, logos, diagrams, tables, signatures, barcodes |

### Custom Query Mode

**Format:** Separate items with ` . ` (period with spaces)

**Examples:**
```
red cars . blue trucks . motorcycles
people wearing helmets . safety vests
fire exits . emergency lights . first aid kits
damaged items . broken parts . missing components
text . logos . QR codes . barcodes
warning signs . hazard symbols . safety labels
```

**Tips:**
- Be specific: "red car" not just "car"
- Use attributes: colors, states, conditions
- Use plural for multiple: "people wearing hats"
- Separate clearly with ` . `

---

## 💬 Chat Mode Detection

1. **Select image** in workspace
2. **Open chat session** (any provider)
3. **Type detection request:**
   - "find red cars"
   - "detect people wearing hats"
   - "show me safety equipment"
   - "locate fire exits"
   - "count damaged items"

GroundingDINO automatically detects and responds!

**Keywords recognized:**
- find, detect, locate, show, identify
- search for, look for, where is/are
- count, how many

---

## ⚙️ Settings

| Setting | Range | Default | Purpose |
|---------|-------|---------|---------|
| **Confidence** | 1-95% | 25% | Minimum detection confidence |
| **Detection Mode** | Auto/Custom | Auto | Use preset or custom query |

**Lower confidence** = More detections (may include false positives)
**Higher confidence** = Fewer detections (more certain)

---

## 🎨 Detection Output

**Standalone Mode** (GroundingDINO):
```
🎯 GroundingDINO Detection Results
=================================

Query: "red cars . people wearing hats"

✓ red cars (3 found)
  1. red cars - 87% confidence - Location: middle-center - Size: medium
  2. red cars - 76% confidence - Location: middle-right - Size: large
  3. red cars - 65% confidence - Location: bottom-left - Size: small

✓ people wearing hats (2 found)
  1. people wearing hats - 92% confidence - Location: top-center - Size: medium
  2. people wearing hats - 81% confidence - Location: middle-left - Size: small

Summary: 5 total detections across 2 object types
```

**Hybrid Mode** (GroundingDINO + Ollama):
- Detection results PLUS natural language description from Ollama
- Best of both worlds!

---

## 🆚 GroundingDINO vs YOLO

| Feature | GroundingDINO | YOLO |
|---------|--------------|------|
| **Object Types** | Unlimited | 80 classes only |
| **Flexibility** | Any text description | Fixed classes |
| **Attributes** | Yes (colors, states) | No |
| **Natural Language** | Yes | No |
| **Chat Integration** | Yes | No |
| **Speed** | Medium | Fast |
| **Model Size** | ~700MB | 6-140MB |

**Use GroundingDINO when:**
- Need unlimited object types
- Want to detect specific attributes
- Need flexible, changing detection needs
- Chat-based interaction desired

**Use YOLO when:**
- Only need common objects (80 classes)
- Need fastest possible speed
- Want smallest model size

---

## 🐛 Troubleshooting

**"No models available"** in dropdown
- ✓ Fixed! Should show "Detection configured below"
- Settings are in the GroundingDINO controls section

**Model download fails**
- Check internet connection
- Check firewall settings
- Try again - downloads resume automatically
- Manual cache location: `~/.cache/groundingdino/`

**Detection too slow**
- First use: Model is downloading (~700MB)
- CPU mode: Normal, but slower than GPU
- GPU mode: Install CUDA-enabled PyTorch for speed

**No objects detected**
- Lower confidence threshold
- Try more general terms
- Check image quality and lighting
- Try different query phrasing

**Installation fails**
- Windows: Install Visual C++ Build Tools
- Update pip: `python -m pip install --upgrade pip`
- Try with admin: Run Command Prompt as Administrator
- Manual: `pip install groundingdino-py torch torchvision --user`

---

## 📚 More Information

- **Full Guide:** `USER_SETUP_GUIDE.md` (GroundingDINO section)
- **Model Download:** `GROUNDING_DINO_MODEL_DOWNLOAD.md`
- **Implementation Details:** `docs/GROUNDING_DINO_GUIDE.md`
- **What's Included:** `WHATS_INCLUDED.txt`

---

## 💡 Pro Tips

1. **Use Hybrid Mode** for best results (detection + description)
2. **Be specific** in custom queries: "red Toyota" not just "car"
3. **Adjust confidence** based on your needs: lower for more results
4. **Use chat mode** for iterative refinement: "find more specific things"
5. **Try presets first** before custom queries - they're well-tuned
6. **Wait for first download** - subsequent uses are instant
7. **GPU recommended** but CPU works fine (just slower)

---

**Quick Start:** Run `install_groundingdino.bat` → Wait for install → Restart ImageDescriber → Select GroundingDINO provider → Detect anything!
