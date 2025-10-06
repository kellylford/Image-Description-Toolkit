# Workflow Statistics Analyzer

## Overview

The `analyze_workflow_stats.py` script analyzes and compares performance statistics from all workflow runs, providing detailed timing metrics, throughput analysis, and comparative rankings.

## What It Does

- Parses workflow logs from all `wf_*` directories
- Extracts individual image processing times
- Calculates comprehensive statistics:
  - Average, min, max, median processing times
  - Standard deviation (consistency)
  - Throughput (images per minute)
  - Total duration and file counts
  - Video and frame extraction statistics

## Usage

Simply run the script from the project root:

```bash
python analyze_workflow_stats.py
```

This will:
1. Analyze all workflow directories
2. Display a comprehensive comparison report
3. Save detailed JSON statistics to `workflow_statistics.json`

## Output

### Console Report Includes:

#### 📊 Individual Workflow Statistics
- Start/End times
- Total duration (formatted)
- Files, videos, frames processed
- Timing metrics (avg, min, max, median)
- Number of samples analyzed

#### 📈 Comparison Table
Side-by-side comparison of all workflows with key metrics

#### 🏆 Rankings
- **Fastest Average**: Which provider processes images quickest
- **Most Consistent**: Lowest processing time variation (smallest range)
- **Highest Throughput**: Most images per minute

#### 📊 Aggregate Statistics
- Combined totals across all workflows
- Overall averages and medians
- Grand total processing times

### JSON Output

`workflow_statistics.json` contains:
- All individual processing times for each workflow
- Detailed metrics for each run
- Timestamp of analysis
- Complete raw data for further analysis

## Current Results (Latest Run)

### Completed Workflows:

| Provider | Avg Time | Min | Max | Median | Throughput |
|----------|----------|-----|-----|--------|------------|
| **Claude Haiku** | 4.69s | 0.83s | 7.29s | 2.53s | 12.8 img/min |
| **Claude Sonnet** | 12.49s | 1.09s | 158.23s | 10.25s | 4.8 img/min |
| **OpenAI GPT-4o-mini** | *Analyzing...* | - | - | - | - |

### In Progress:
- Ollama LLaVA
- ONNX LLaVA

## Re-running

You can re-run the script at any time to update statistics as workflows complete:

```bash
python analyze_workflow_stats.py
```

The script will automatically:
- Detect newly completed workflows
- Include updated timing data
- Recalculate all statistics and rankings

## Key Insights from Latest Analysis

### 🏆 Performance Winner: Claude Haiku
- **Fastest**: 4.69s average per image
- **Most Consistent**: Only 6.46s range (0.83s to 7.29s)
- **Highest Throughput**: 12.8 images/minute
- **Total Time**: 2h 36m for 1,804 descriptions

### 📊 Claude Sonnet Characteristics
- **More Thorough**: 12.49s average (2.7x slower than Haiku)
- **Less Consistent**: Wide range (1.09s to 158.23s)
- **High Quality**: Likely more detailed descriptions
- **Total Time**: 6h 34m for 1,804 descriptions

### 💡 Practical Takeaways
1. **For Speed**: Use Claude Haiku (12.8 images/min)
2. **For Quality**: Use Claude Sonnet (more processing time = more detail)
3. **For Consistency**: Claude Haiku has minimal variation
4. **For Large Batches**: Haiku completes ~2.5x faster

## Files

- **Script**: `analyze_workflow_stats.py`
- **Input**: `wf_*/logs/workflow_*.log` and `wf_*/logs/image_describer_*.log`
- **Output**: 
  - Console report (stdout)
  - `workflow_statistics.json` (detailed data)

## Statistics Explained

### Timing Metrics:
- **Average Time**: Mean processing time per image
- **Min/Max Time**: Fastest and slowest individual image
- **Median Time**: Middle value (less affected by outliers)
- **Std Dev**: Measure of consistency (lower = more consistent)

### Throughput:
- **Images/Minute**: How many images processed per minute
- Higher is better for batch processing

### Consistency:
- **Range**: Difference between max and min times
- Smaller range = more predictable performance

## Technical Details

The script analyzes:
1. **Workflow Logs**: Overall timing and file counts
2. **Image Describer Logs**: Individual processing times for each image
3. **Frame Extractor Logs**: Video and frame statistics

All timing data is extracted from actual log entries, ensuring accuracy.
