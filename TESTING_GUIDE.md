# ImageDescriber Comprehensive Testing Guide

This directory contains a Python script to automatically test all available Ollama models with all available prompt styles on a batch of test images.

## File Created

**`comprehensive_test.py`** - Python comprehensive testing script with full features

## Prerequisites

1. **Ollama installed and running** with at least one model:
   ```bash
   ollama pull llava:7b
   ollama pull moondream
   ollama pull gemma2:2b      # Great for descriptions!
   ollama pull llama3.2-vision:11b
   ```

2. **Test images** - A small directory with 3-10 images for testing

## Usage

```bash
python comprehensive_test.py "C:\path\to\test\images"
python comprehensive_test.py "C:\path\to\test\images" --output-dir "custom_results"
```

## What It Does

1. **Queries Ollama** - Automatically detects ALL installed models (not just vision models)
2. **Reads Config** - Extracts all available prompt styles from `image_describer_config.json`
3. **Runs Complete Workflow** - Tests every model with every prompt style through ALL FOUR STEPS:
   - Video frame extraction
   - Image conversion (HEIC to JPG) 
   - AI description generation
   - HTML report creation
4. **Organizes Output** - Creates timestamped directory with results for each combination
5. **Generates Comprehensive Reports** - Multiple report formats with detailed statistics

## Example Output Structure

## Example Output Structure

```
comprehensive_test_20250728_143022/
├── comprehensive_test_report.txt         # Human-readable detailed report
├── comprehensive_test_data.csv           # CSV data for analysis
├── test_statistics.txt                   # Performance statistics by model/prompt
├── failure_analysis.txt                  # Detailed failure analysis (if any failures)
├── comprehensive_test_visual_report.html # Visual HTML report comparing all results
├── moondream_latest_detailed/            # Results for moondream:latest + detailed
│   ├── extracted_frames/                 #   Video frames (if any videos)
│   ├── converted_images/                 #   HEIC conversions (if any HEIC files)
│   ├── descriptions/                     #   AI-generated descriptions
│   │   └── image_descriptions.txt
│   ├── html_reports/                     #   HTML galleries
│   │   └── image_descriptions.html
│   └── logs/                             #   Processing logs
├── gemma2_2b_artistic/                   # Results for gemma2:2b + artistic
│   └── ... (same structure)
└── ... (all other combinations)
```

## Benefits

- **Complete Pipeline Testing** - Tests all four workflow steps for every combination
- **Detailed Performance Analysis** - Per-model and per-prompt timing and success rates
- **Comprehensive Reporting** - Multiple report formats (text, CSV, statistics, failure analysis)
- **Failure Investigation** - Detailed error analysis with specific failure reasons
- **Automated** - No manual intervention required
- **Organized Results** - Easy to compare outputs across models and prompts
- **Data Export** - CSV format for spreadsheet analysis

## New Python Script Features

The Python version (`comprehensive_test.py`) provides significant improvements:

### Advanced Reporting
- **Performance Statistics** - Total time per model, average time per prompt
- **Success Rate Analysis** - Success/failure rates by model and prompt
- **Failure Analysis** - Grouped error types and detailed failure investigation
- **CSV Export** - All data exportable for statistical analysis

### Better Error Handling
- **Timeout Protection** - 30-minute timeout per combination
- **Detailed Error Messages** - Specific failure reasons captured
- **Output Analysis** - Checks what files were actually created

### Comprehensive Statistics
- Total runtime for entire test
- Per-model performance (total time, average time, success rate)
- Per-prompt performance across all models
- File creation statistics (descriptions, HTML, frames, conversions)

## Comprehensive Output Formats & Usage

The Python testing script generates **five** detailed report formats, each optimized for different analysis needs:

### 1. **`comprehensive_test_report.txt`** - Main Human-Readable Report

**Purpose:** Primary report for manual review and overview  
**Best for:** Quick assessment, sharing results, understanding overall performance

**Contains:**
```
ImageDescriber Comprehensive Test Report
=======================================

Test Date: 2025-07-28 14:30:22
Image Path: C:\Users\kelly\Pictures\test_images  
Total Runtime: 2:45:33
Total Combinations: 24
Successful: 21
Failed: 3
Success Rate: 87.5%

Detailed Results:
-----------------
✅ SUCCESS: gemma2:2b + detailed (156.3s)
  Output: comprehensive_test_20250728/gemma2_2b_detailed
  Created: descriptions (15,847 bytes), HTML (1 files), logs

❌ FAILED: llama3.2-vision:11b + technical (45.2s)
  Error: Model timeout - insufficient memory
  Output: comprehensive_test_20250728/llama3_2_vision_11b_technical  
  Created: descriptions (8,231 bytes), logs

✅ SUCCESS: moondream:latest + artistic (89.7s)
  Output: comprehensive_test_20250728/moondream_latest_artistic
  Created: descriptions (12,456 bytes), HTML (1 files), frames (15), logs
```

**How to Use:**
- Read first for overall test success/failure
- Identify which model/prompt combinations failed
- See what files were actually created for each test
- Get rough timing estimates for planning future runs

### 2. **`comprehensive_test_data.csv`** - Raw Data for Analysis

**Purpose:** Machine-readable data for statistical analysis  
**Best for:** Excel/spreadsheet analysis, data visualization, automated processing

**CSV Columns:**
```
Model,Prompt,Success,Duration_Seconds,Error_Message,Output_Directory,
Descriptions_Created,HTML_Created,Frames_Extracted,Images_Converted,
Logs_Created,Description_File_Size,HTML_File_Count,Frame_Count,Converted_Count
```

**Example Data:**
```csv
gemma2:2b,detailed,True,156.3,,/path/to/output,True,True,False,False,True,15847,1,0,0
llama3.2-vision:11b,technical,False,45.2,Model timeout,/path/to/output,True,False,False,False,True,8231,0,0,0
moondream:latest,artistic,True,89.7,,/path/to/output,True,True,True,False,True,12456,1,15,0
```

**How to Use:**
- **Import into Excel/Google Sheets** for pivot tables and charts
- **Filter by Success=False** to analyze only failures  
- **Sort by Duration_Seconds** to find fastest/slowest combinations
- **Group by Model** to compare model performance
- **Group by Prompt** to see which prompts work best across models
- **Create charts** showing success rates, timing distributions, etc.

**Analysis Examples:**
```excel
=AVERAGE(IF(A:A="gemma2:2b",D:D))           # Average time for gemma2:2b
=COUNTIFS(A:A="moondream*",C:C=TRUE)        # Successful moondream runs  
=MAXIFS(D:D,C:C=TRUE)                       # Longest successful run time
```

### 3. **`test_statistics.txt`** - Performance Analytics

**Purpose:** Detailed performance analysis and comparisons  
**Best for:** Model selection, performance optimization, capacity planning

**Contains:**
```
ImageDescriber Test Statistics
=============================

Model Performance Statistics:
-----------------------------

gemma2:2b:
  Total Time: 0:15:23
  Average Time: 154.2s
  Successes: 5/6
  Success Rate: 83.3%
  Per-prompt breakdown:
    ✅ detailed: 145.3s
    ✅ concise: 134.7s  
    ✅ artistic: 167.8s
    ✅ technical: 142.1s
    ✅ colorful: 189.5s
    ❌ narrative: timeout

moondream:latest:
  Total Time: 0:08:45
  Average Time: 87.5s
  Successes: 6/6
  Success Rate: 100.0%
  Per-prompt breakdown:
    ✅ detailed: 89.3s
    ✅ concise: 78.2s
    ✅ artistic: 95.1s
    ✅ technical: 82.7s
    ✅ colorful: 98.8s
    ✅ narrative: 80.9s

Prompt Style Statistics:
------------------------

detailed:
  Total Time: 0:12:34
  Average Time: 125.7s
  Successes: 3/4
  Success Rate: 75.0%

artistic:
  Total Time: 0:14:21  
  Average Time: 143.5s
  Successes: 4/4
  Success Rate: 100.0%
```

**How to Use:**
- **Model Selection:** Compare success rates and average times
- **Capacity Planning:** Use total times to estimate full test runs
- **Prompt Optimization:** See which prompts work reliably across models
- **Resource Planning:** Identify memory-intensive models (low success rates)
- **Benchmark Comparison:** Track performance changes over time

### 4. **`failure_analysis.txt`** - Detailed Error Investigation

**Purpose:** Troubleshooting and debugging failed combinations  
**Best for:** Fixing configuration issues, understanding model limitations

**Contains:**
```
Failure Analysis Report
======================

Total Failures: 3

Failures by Error Type:
----------------------

Model timeout - insufficient memory (2 occurrences):
  - llama3.2-vision:11b + technical
  - llama3.2-vision:11b + detailed

File not found: descriptions_to_html.py (1 occurrence):
  - bakllava:latest + colorful

Detailed Failure Information:
----------------------------

❌ llama3.2-vision:11b + technical:
  Duration: 45.2s
  Error: Model timeout - insufficient memory
  Output Dir: /path/to/llama3_2_vision_11b_technical
  stderr: RuntimeError: CUDA out of memory. Tried to allocate 2.25 GiB...

❌ bakllava:latest + colorful:
  Duration: 12.1s  
  Error: File not found: descriptions_to_html.py
  Output Dir: /path/to/bakllava_latest_colorful
  stderr: FileNotFoundError: [Errno 2] No such file or directory...
```

**How to Use:**
- **Identify Patterns:** See if certain models consistently fail
- **Resource Issues:** Spot memory/GPU limitations
- **Configuration Problems:** Find missing dependencies or files
- **Model Compatibility:** Understand which models work with your setup
- **Targeted Fixes:** Focus debugging efforts on specific error types

### 5. **`comprehensive_test_visual_report.html`** - Interactive Visual Comparison

**Purpose:** Visual comparison of all successful results with actual descriptions  
**Best for:** Quality assessment, model comparison, prompt effectiveness evaluation

**Features:**
- **Organized by Prompt Style:** Each prompt gets its own section showing all models that succeeded
- **Model Performance Cards:** Each model shows timing and sample descriptions
- **Responsive Design:** Works on desktop and mobile devices
- **Table of Contents:** Quick navigation between prompt styles
- **Test Summary:** Overview statistics and test information

**Content Structure:**
```html
📋 Table of Contents
├── 🎯 Artistic Style (6 models)
├── 🎯 Detailed Style (5 models)  
├── 🎯 Technical Style (4 models)
└── 📸 Test Images Used

For each prompt style:
├── 🤖 Model Cards (sorted by speed)
│   ├── ⏱️ Processing Time
│   ├── Sample Descriptions (first 2 images)
│   └── Total Description Count
└── Performance Summary
```

**How to Use:**
- **Open in any web browser** to see visual results
- **Compare prompt effectiveness** - see which prompts work well across models
- **Evaluate model quality** - read actual generated descriptions side-by-side
- **Speed comparison** - models sorted by processing time within each prompt
- **Quality assessment** - quickly spot models producing poor descriptions
- **Model discovery** - find unexpected models that work well for descriptions

**Perfect for:**
- **Manual quality review** before selecting models for production
- **Sharing results** with team members or stakeholders
- **Prompt optimization** - understanding how different prompts affect output
- **Model evaluation** - side-by-side comparison of description quality

## Practical Usage Workflows

### **Workflow 1: Model Selection for Production**
1. **Run comprehensive test** on representative images
2. **Check `test_statistics.txt`** for success rates and timing
3. **Open CSV in Excel** to create performance comparison charts
4. **Select models** with >95% success rate and acceptable timing
5. **Verify in `comprehensive_test_report.txt`** that selected models created all required outputs

### **Workflow 2: Troubleshooting Failed Models**
1. **Check `failure_analysis.txt`** for error patterns
2. **Group similar errors** (memory issues, missing files, etc.)
3. **Use detailed stderr output** to diagnose specific problems
4. **Fix underlying issues** (install dependencies, increase memory, etc.)
5. **Re-run test** on previously failed combinations

### **Workflow 3: Performance Optimization**
1. **Import CSV into spreadsheet** application
2. **Create pivot table** by Model vs Prompt showing average duration
3. **Identify fastest models** for each prompt style
4. **Check quality** by manually reviewing generated descriptions
5. **Balance speed vs quality** for your use case

### **Workflow 4: Quality Assessment**
1. **Open `comprehensive_test_visual_report.html`** in your web browser
2. **Browse by prompt style** to see how different prompts perform across models
3. **Read sample descriptions** to evaluate quality and style consistency
4. **Compare models within each prompt** - they're sorted by processing speed
5. **Document preferred combinations** for different image types and use cases

### **Workflow 5: Regression Testing**
1. **Save baseline test results** before making changes
2. **Run comprehensive test** after updates
3. **Compare CSV files** to identify performance regressions
4. **Check failure analysis** for new error types
5. **Validate that success rates haven't decreased**

## Tips for Effective Analysis

- **Start with the HTML visual report** for an intuitive overview of quality and performance
- **Use the main text report** for detailed success/failure analysis
- **Use CSV data for quantitative analysis** (timing, success rates)
- **Use statistics report for model comparison** and selection
- **Use failure analysis only when needed** for troubleshooting
- **Save all reports** for historical comparison and trend analysis
- **Import CSV into your preferred analysis tool** (Excel, Python, R, etc.)
- **Share the HTML report** with team members for collaborative model selection

## Use Cases

- **Model Comparison** - See which models perform best for your use case
- **Prompt Testing** - Compare different prompt styles on the same images
- **Performance Benchmarking** - Measure processing times across models
- **Quality Assessment** - Manually review outputs to find optimal combinations
- **Regression Testing** - Ensure updates don't break existing functionality

## Tips

- Use a small set of representative test images (3-10 images)
- Choose images that represent your typical use case
- Review the generated descriptions to find your preferred model/prompt combinations
- Check processing times if performance is important for your workflow
- **Models like gemma2 and llama3.2 work great for descriptions even if not labeled as "vision" models**
- Directory names are automatically sanitized (colons become underscores, spaces removed)

## Recent Fixes (v3)

- ✅ Fixed WMIC timestamp issue (now uses PowerShell for reliable timestamps)
- ✅ Fixed directory naming with colons in model names (llava:latest → llava_latest)
- ✅ Fixed UTF-8 BOM issues in config file reading
- ✅ Now includes ALL models, not just "vision" models (includes gemma2, llama3, etc.)
- ✅ Improved error handling and directory sanitization
- ✅ **Fixed missing HTML reports** - Now runs `--steps describe,html` instead of just `describe`
- ✅ **Simplified to single Python script** - Removed batch and PowerShell versions for better maintainability
- ✅ **Fixed duplicate output issue** - No longer creates files in multiple directories
- ✅ **Added comprehensive HTML visual report** - Interactive comparison organized by prompt style and model
