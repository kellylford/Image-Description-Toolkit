# Analysis Tools for Image Description Toolkit

This directory contains three powerful analysis tools for evaluating and comparing workflow results from the Image Description Toolkit.

## 📋 Table of Contents

- [Overview](#overview)
- [Tools](#tools)
  - [1. combine_workflow_descriptions.py](#1-combine_workflow_descriptionspy)
  - [2. stats_analysis.py](#2-stats_analysispy)
  - [3. content_analysis.py](#3-content_analysispy)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Common Use Cases](#common-use-cases)
- [Output Files](#output-files)
- [Tips and Best Practices](#tips-and-best-practices)

---

## Overview

These analysis tools help you:

- **Compare descriptions** from different AI models side-by-side
- **Measure performance** (speed, throughput, consistency) across providers
- **Analyze content quality** (vocabulary richness, word frequencies, style patterns)
- **Make informed decisions** about which AI model to use for your needs

All tools are designed to:
- ✅ **Preserve your data** - Never overwrite existing files (auto-numbering)
- ✅ **Be flexible** - Custom input/output locations via command-line arguments
- ✅ **Work together** - Outputs from one tool feed into the next

---

## Tools

### 1. combine_workflow_descriptions.py

**Purpose:** Combines descriptions from multiple workflow runs into a single CSV file for easy comparison.

**What it does:**
- Reads `image_descriptions.txt` from all workflow directories
- Creates a side-by-side CSV with one row per image
- Each column represents a different AI model's description
- **NEW in v2.0:** Sorts images chronologically by photo date (EXIF data) - oldest to newest
- Uses intelligent EXIF extraction: DateTimeOriginal → DateTimeDigitized → DateTime → file mtime
- Alternative alphabetical sorting available with `--sort name`

**When to use:**
- After running multiple workflows with different AI models
- When you want to compare descriptions for the same images
- Before running word frequency analysis

#### Usage

```bash
# Basic usage - creates CSV sorted by photo date (NEW DEFAULT!)
python combine_workflow_descriptions.py

# Sort alphabetically by filename (legacy behavior)
python combine_workflow_descriptions.py --sort name

# Create tab-separated file with date sorting
python combine_workflow_descriptions.py --format tsv --sort date --output results.tsv

# Use legacy @-separated format with alphabetical sorting
python combine_workflow_descriptions.py --format atsv --sort name --output results.txt

# Specify custom workflow directory with date sorting
python combine_workflow_descriptions.py --input-dir /path/to/workflows --sort date

# Combine all options
python combine_workflow_descriptions.py --input-dir /data/workflows --format tsv --sort name
```

#### Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--input-dir` | `../Descriptions` | Directory containing `wf_*` workflow folders |
| `--output` | `combineddescriptions.csv` | Output filename (saved in analysis/results/ directory) |
| `--format` | `csv` | Output format: `csv` (standard comma-delimited), `tsv` (tab-delimited), or `atsv` (@-separated legacy) |
| `--sort` | `date` | **NEW!** Sort order: `date` (chronological by EXIF photo date) or `name` (alphabetical by filename) |

#### Output

Creates a file with:
- **Column 1:** Image Name (e.g., IMG_1234.JPG)
- **Columns 2-N:** Description from each AI model

**Format Options:**
- **CSV (default):** Standard comma-delimited with quoted fields
  - ✅ Opens directly in Excel with proper column separation
  - ✅ Standard format recognized by all tools
  - Best for: General use, sharing with others
  
- **TSV:** Tab-delimited values
  - ✅ Opens directly in Excel with proper column separation
  - ✅ No quoting needed, easier to read in text editors
  - Best for: Long descriptions, manual text review
  
- **ATSV:** @-separated values (legacy)
  - ⚠️ Requires Excel Data > From Text/CSV import wizard
  - Still supported for backward compatibility
  - Best for: Existing workflows that expect @ delimiter

**Example CSV output:**
```csv
"Image Name","Prompt","Workflow","Claude Haiku 3","OpenAI GPT-4o","Ollama LLaVA"
"IMG_1234.JPG","narrative","vacation_photos","The image shows a red car...","A red vehicle is...","In this picture..."
```

**Note:** The "Workflow" column identifies which workflow processed the image. This is especially useful when:
- Processing the same images multiple times with different settings
- Comparing results from different workflow runs  
- Tracking workflow versions and iterations
- Workflows without metadata show "(legacy)" in the Workflow column

**Example TSV output:**
```tsv
Image Name	Prompt	Workflow	Claude Haiku 3	OpenAI GPT-4o	Ollama LLaVA
IMG_1234.JPG	narrative	vacation_photos	The image shows a red car...	A red vehicle is...	In this picture...
```

---

### 2. stats_analysis.py

**Purpose:** Analyzes performance metrics from workflow logs.

**What it does:**
- Parses workflow log files to extract timing data
- Calculates statistics: avg time/image, min/max times, throughput
- Tracks HEIC conversion metrics (files converted, conversion time)
- Identifies which specific images were fastest/slowest
- Ranks models by speed, consistency, and throughput
- Exports to both CSV and JSON formats

**When to use:**
- To measure and compare AI model performance
- To identify bottlenecks in your workflow
- To see which models are fastest/most cost-effective
- To track HEIC conversion overhead

#### Usage

```bash
# Basic usage (analyzes all workflows in Descriptions directory)
python stats_analysis.py

# Specify custom workflow directory
python stats_analysis.py --input-dir /path/to/workflows

# Custom output filenames
python stats_analysis.py --csv-output timing_stats.csv --json-output stats.json

# Full custom usage
python stats_analysis.py --input-dir /data/workflows --csv-output my_stats.csv
```

#### Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--input-dir` | `../Descriptions` | Directory containing `wf_*` workflow folders |
| `--csv-output` | `workflow_timing_stats.csv` | CSV output filename (saved in analysis/results/ directory) |
| `--json-output` | `workflow_statistics.json` | JSON output filename (saved in analysis/results/ directory) |

#### Output

**Console Display:**
```
Claude Haiku 3
--------------------------------------------------------------------------------
  Start Time:              2025-10-07 10:09:26
  End Time:                2025-10-07 10:12:40
  Total Duration:          3m 14s (3.2 minutes)
  Files Processed:         78
  Videos Found:            10
  Frames Extracted:        10

  HEIC Conversion:
    Files Found:           27
    Files Converted:       27
    Conversion Time:       3m 10s
    Already JPG/PNG:       41

  Description Generation:
    Average Time/Image:    4.36s
    Min Time:              0.93s (IMG_9292.jpg)
    Max Time:              6.82s (photo-10491_singular_display_fullPicture.jpg)
    Median Time:           2.39s
    Samples:               40 images (excludes extracted frames)
```

**CSV Export:** Detailed metrics for Excel/data analysis
**JSON Export:** Complete raw statistics for programmatic access

---

### 3. content_analysis.py

**Purpose:** Analyzes word frequencies and vocabulary across AI model descriptions.

**What it does:**
- Counts word frequencies in descriptions
- Measures vocabulary richness (% unique words)
- Tracks description length and sentence count
- Categorizes words (colors, emotions, technical terms)
- Identifies common words (used by all models)
- Finds unique words (used by only one model)
- Compares verbosity and descriptive style

**When to use:**
- To understand how different AI models "speak"
- To compare description quality and detail level
- To find which models focus on colors, emotions, technical details
- To discover unique vocabulary patterns per model

#### Usage

```bash
# Basic usage (analyzes combineddescriptions.csv - auto-detects format)
python content_analysis.py

# Analyze specific combined descriptions file (works with CSV, TSV, or ATSV)
python content_analysis.py --input my_descriptions.csv

# Analyze TSV file
python content_analysis.py --input results.tsv

# Custom output filename
python content_analysis.py --output word_analysis.csv

# Full custom usage
python content_analysis.py --input my_descriptions.csv --output my_analysis.csv
```

#### Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--input` | `combineddescriptions.csv` | Input file with combined descriptions (CSV, TSV, or ATSV - auto-detected) |
| `--output` | `description_content_analysis.csv` | Output CSV filename (saved in analysis/results/ directory) |

**Note:** Input file is read from the `analysis/results/` directory by default (typically created by `combine_workflow_descriptions.py`). For backward compatibility, it will also check the `analysis/` directory if not found in `results/`.

#### Output

**Console Display:**
```
Claude Haiku 3
--------------------------------------------------------------------------------
  Descriptions Analyzed:   323
  Total Words:             29,955
  Vocabulary Size:         2,173 unique words
  Vocabulary Richness:     11.8%

  Per Description:
    Avg Words:             92.7
    Avg Unique Words:      50.2
    Avg Sentences:         5.9

  Descriptive Categories:
    Color Words:           983 times
    Emotion/Tone Words:    234 times
    Technical Terms:       347 times

  Top 15 Words:
     1. image                (416 times)
     2. there                (314 times)
     3. overall              (272 times)
     ...

📚 Vocabulary Richness (% unique words):
  1. Ollama LLaVA-Phi3                     78.1%
  2. Claude Haiku 3.5                      72.6%
  ...

📝 Average Description Length (words/description):
  1. Ollama LLaVA 7B                      273.7 words/description
  2. Ollama LLaVA 34B                     249.0 words/description
  ...

🎨 Color Word Usage:
  1. Claude Haiku 3                      983 times (3.0 per description)
  ...
```

**CSV Export:** All vocabulary metrics for deeper analysis

---

## Installation

These tools use only Python standard library modules. No additional dependencies required!

Requirements:
- Python 3.8 or higher
- Standard library modules: `argparse`, `csv`, `re`, `pathlib`, `statistics`, `json`, `collections`

---

## Quick Start

### Complete Analysis Workflow

Here's how to run a complete analysis from start to finish:

```bash
# 1. Navigate to the analysis directory
cd analysis

# 2. Combine descriptions from all workflows
python combine_workflow_descriptions.py

# 3. Analyze performance statistics
python stats_analysis.py

# 4. Analyze word frequencies
python content_analysis.py

# Done! Check the output files in the analysis/ directory
```

### Custom Workflow Directory

If your workflows are in a different location:

```bash
cd analysis

# Specify custom directory for all tools
python combine_workflow_descriptions.py --input-dir /path/to/workflows
python stats_analysis.py --input-dir /path/to/workflows
python content_analysis.py  # Uses the combined file from step 1
```

---

## Common Use Cases

### Scenario 1: Testing Multiple AI Models

**Goal:** Compare 5 different AI models to choose the best one

```bash
# After running workflows with 5 models...

cd analysis

# 1. Create side-by-side comparison
python combine_workflow_descriptions.py --output model_comparison.csv

# 2. Get performance metrics
python stats_analysis.py --csv-output performance_comparison.csv

# 3. Analyze description quality
python content_analysis.py --input model_comparison.csv --output quality_analysis.csv
```

**Results:**
- `model_comparison.csv` - Read descriptions side-by-side
- `performance_comparison.csv` - See which is fastest
- `quality_analysis.csv` - See which has best vocabulary/style

### Scenario 2: Before/After Comparison

**Goal:** Compare results before and after changing prompts

```bash
cd analysis

# Analyze "before" workflows
python combine_workflow_descriptions.py --output before_descriptions.csv
python stats_analysis.py --csv-output before_stats.csv

# Run new workflows with updated prompts...

# Analyze "after" workflows
python combine_workflow_descriptions.py --output after_descriptions.csv
python stats_analysis.py --csv-output after_stats.csv

# Compare the CSV files to see improvements
```

### Scenario 3: Production Monitoring

**Goal:** Track performance over time

```bash
cd analysis

# Monthly analysis with dated filenames
python stats_analysis.py --csv-output stats_2025_01.csv
# Next month...
python stats_analysis.py --csv-output stats_2025_02.csv
# Compare trends over time
```

---

## Output Files

### File Safety

**All tools protect your existing files!**

If a file already exists, the tool automatically adds a number:
- `output.csv` → `output_1.csv` → `output_2.csv` → etc.

This ensures you never accidentally overwrite previous analysis results.

### Default Output Locations

All output files are saved in the `analysis/results/` directory by default:

| Tool | Default Output Files |
|------|---------------------|
| combine_workflow_descriptions.py | `results/combineddescriptions.csv` (or `.tsv`/`.txt` depending on format) |
| stats_analysis.py | `results/workflow_timing_stats.csv`<br>`results/workflow_statistics.json` |
| content_analysis.py | `results/description_content_analysis.csv` |

**Why a separate results directory?**
- ✅ Keeps the analysis directory clean and organized
- ✅ Makes it easy to find all results in one place  
- ✅ Prevents polluting the repository with output files
- ✅ Results are automatically excluded from git (via `.gitignore`)

**Note:** You can override the default location by specifying a full path with `--output`

### Understanding Output Files

#### combineddescriptions.csv (or .tsv/.txt)
- **Formats Available:**
  - `.csv` - Standard CSV (comma-delimited, quoted fields) - **Recommended**
  - `.tsv` - Tab-separated values - Good for Excel, easier to read in text editors
  - `.txt` - @-separated (legacy format) - Requires Excel import wizard
- **Use:** Compare descriptions visually side-by-side
- **Open with:** Excel (double-click for CSV/TSV), LibreOffice, any text editor
- **Excel Tip:** CSV and TSV formats open directly with proper columns - no import wizard needed!
- **Search Tip:** Find specific images to see all model descriptions at once

#### workflow_timing_stats.csv
- **Format:** Standard CSV
- **Columns:** Model, Speed, HEIC conversions, Min/Max times, Throughput
- **Use:** Performance comparison in Excel
- **Tip:** Sort by "Avg Time/Image" to find fastest model

#### workflow_statistics.json
- **Format:** JSON
- **Use:** Programmatic access to all statistics
- **Tip:** Import into Python for custom analysis

#### description_content_analysis.csv
- **Format:** Standard CSV
- **Columns:** Model, Word counts, Vocabulary stats, Top words
- **Use:** Quality comparison in Excel
- **Tip:** Sort by "Vocabulary Richness %" to find most varied descriptions

---

## Tips and Best Practices

### Date Sorting Tips (NEW in v2.0)

1. **Chronological Organization**
   - **Default behavior:** Images sorted by actual photo date (EXIF data)
   - Perfect for vacation photos, events, time-series analysis
   - Shows images in the order you actually took them

2. **When to Use Alphabetical Sorting**
   - Add `--sort name` for filename-based sorting
   - Useful when filenames have meaningful sequence (IMG_001, IMG_002...)
   - Better for systematically named photos or screenshots

3. **EXIF Date Extraction**
   - Uses DateTimeOriginal (when photo was taken) when available
   - Falls back to DateTimeDigitized → DateTime → file modification time
   - Works across workflow subdirectories (converted_images, extracted_frames)

### Performance Tips

1. **Speed vs Quality Tradeoff**
   - Use `stats_analysis.py` to find fastest models
   - Use `content_analysis.py` to find most detailed models
   - Balance based on your needs

2. **HEIC Conversion Impact**
   - Check "Conversion Time" in workflow stats
   - If high, consider pre-converting images to JPG
   - Conversion time is separate from description time

3. **Identify Slow Images**
   - Check "Max Time File" to see which images are slowest
   - Look for patterns (large files? complex scenes?)
   - Optimize or exclude problematic images

### Quality Tips

1. **Vocabulary Richness**
   - Higher % = more varied word usage
   - 50-70% is good for image descriptions
   - Too high might mean inconsistent terminology

2. **Description Length**
   - Longer isn't always better
   - Compare with your needs (captions vs detailed descriptions)
   - Consistent length across images is often desirable

3. **Category Analysis**
   - Color words: Important for art, products, fashion
   - Technical terms: Important for documentation, instructional
   - Emotion words: Important for storytelling, marketing

### Workflow Tips

1. **Always Combine First**
   ```bash
   python combine_workflow_descriptions.py
   # Then run the other tools
   ```

2. **Use Meaningful Output Names**
   ```bash
   python stats_analysis.py --csv-output product_photos_jan2025.csv
   # Not just "output.csv"
   ```

3. **Keep Your Analysis Organized**
   ```bash
   # Create subdirectories for different projects
   mkdir analysis/project_A
   python combine_workflow_descriptions.py --output project_A/combined.csv
   ```

4. **Test with Small Datasets First**
   - Run workflows on 10-20 images initially
   - Analyze and choose best model
   - Then run full dataset with chosen model

### Troubleshooting

**"Directory not found" error:**
```bash
# Check where your workflows actually are
ls ../Descriptions/

# Or specify the correct path
python stats_analysis.py --input-dir /actual/path/to/workflows
```

**"No descriptions found" error:**
```bash
# Make sure workflow completed successfully
ls ../Descriptions/wf_*/image_descriptions.txt

# Check log files exist
ls ../Descriptions/wf_*/logs/workflow_*.log
```

**Output files not appearing:**
```bash
# Check current directory
ls -la

# Files are in analysis/ directory
cd analysis
ls -la
```

---

## Advanced Usage

### Batch Processing Multiple Directories

```bash
#!/bin/bash
# analyze_all.sh - Analyze multiple workflow directories

for dir in /data/workflows/*; do
    if [ -d "$dir" ]; then
        name=$(basename "$dir")
        echo "Analyzing $name..."
        python stats_analysis.py --input-dir "$dir" --csv-output "stats_${name}.csv"
    fi
done
```

### Combining Results from Different Dates

```bash
# Combine multiple workflow runs
python combine_workflow_descriptions.py --input-dir ../Descriptions_Week1 --output week1.csv
python combine_workflow_descriptions.py --input-dir ../Descriptions_Week2 --output week2.csv

# Analyze each separately
python content_analysis.py --input week1.csv --output analysis_week1.csv
python content_analysis.py --input week2.csv --output analysis_week2.csv
```

### Custom Analysis Scripts

The JSON output from `stats_analysis.py` can be imported into custom Python scripts:

```python
import json

with open('analysis/workflow_statistics.json') as f:
    stats = json.load(f)

# Custom analysis here
for workflow in stats['workflows']:
    if workflow['average_time_per_image'] < 5.0:
        print(f"Fast model: {workflow['model']}")
```

---

## Support and Contributing

For issues, questions, or feature requests, please refer to the main Image Description Toolkit documentation.

**Remember:**
- These tools are designed to help you make informed decisions about AI model selection
- Always review actual descriptions, not just statistics
- Balance speed, quality, and cost based on your specific needs

Happy analyzing! 🎉
