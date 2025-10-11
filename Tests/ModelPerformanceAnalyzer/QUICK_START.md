# Model Performance Analyzer - Quick Start Guide

## What Does This Tool Do?

Analyzes AI vision model performance by combining:
- **Description quality** (word count, detail level)
- **Performance metrics** (speed, throughput)
- **Cost data** (tokens, pricing)

Generates comprehensive reports comparing all models tested.

## How to Run

### Complete 2-Step Process

```bash
# Step 1: Combine workflow descriptions into one CSV
python analysis/combine_workflow_descriptions.py \
  --input-dir idtexternal/idt/Descriptions \
  --output idtexternal/idt/analysis/results/combineddescriptions.csv

# Step 2: Analyze performance and generate reports
python Tests/ModelPerformanceAnalyzer/model_performance_analyzer.py
```

### When to Run Each Step

**Step 1 (Combine Descriptions)** - Run when:
- ✅ You've completed new workflow runs
- ✅ You want to include new images in analysis
- ✅ The combineddescriptions.csv is missing
- ⏱️ Takes a few minutes with 100+ workflows

**Step 2 (Analyze Performance)** - Run when:
- ✅ After running Step 1
- ✅ Anytime you want fresh analysis
- ⚡ Takes seconds to complete

## What You Get

### Generated Files

1. **`model_analysis_comprehensive.csv`**
   - Every workflow run with complete metrics
   - Sortable, filterable data in Excel/spreadsheet
   - Columns: model, provider, speed, cost, word count, etc.

2. **`model_analysis_blog_post.md`**
   - Human-readable analysis report
   - Rankings by speed, detail, cost
   - Provider comparisons (Claude vs OpenAI vs Ollama)
   - Practical recommendations

### Sample Insights You'll See

```
Fastest Model: Ollama Moondream (6.75s)
Most Detailed: Ollama Gemma3 (444 words)
Most Cost-Effective: Claude Haiku 3.5 ($0.000011/word)
Best Value: Claude Haiku 3.5 ($0.002/image, fast, detailed)
```

## Troubleshooting

### "Descriptions file not found"
**Solution**: Run Step 1 first to generate the combined CSV

### "No descriptions parsed from [Model]"
**Cause**: Some workflow runs may have failed or incomplete data
**Impact**: Those runs are excluded from analysis (expected)

### "Only 26 records combined"
**Cause**: You ran Step 2 without updating combineddescriptions.csv
**Solution**: Run Step 1 to include all your workflow runs

## Quick Reference

| Action | Command |
|--------|---------|
| Update combined descriptions | `python analysis/combine_workflow_descriptions.py --input-dir idtexternal/idt/Descriptions --output idtexternal/idt/analysis/results/combineddescriptions.csv` |
| Run analysis | `python Tests/ModelPerformanceAnalyzer/model_performance_analyzer.py` |
| View CSV results | Open `Tests/ModelPerformanceAnalyzer/model_analysis_comprehensive.csv` in Excel |
| View report | Open `Tests/ModelPerformanceAnalyzer/model_analysis_blog_post.md` in any text editor |

## Where Everything Lives

```
Tests/ModelPerformanceAnalyzer/
├── model_performance_analyzer.py      # Main analysis script
├── model_analysis_comprehensive.csv   # Generated: All metrics
├── model_analysis_blog_post.md       # Generated: Analysis report
├── README.md                          # Detailed documentation
└── QUICK_START.md                    # This file

idtexternal/idt/
├── Descriptions/                      # Input: Workflow directories
└── analysis/results/
    ├── combineddescriptions.csv       # Input: Combined descriptions (from Step 1)
    └── workflow_timing_stats.csv      # Input: Performance metrics
```

## Related Documentation

- **Full Documentation**: `README.md` in this directory
- **GitHub Issue**: #28 - Investigate Model Performance
- **Tool Purpose**: Non-shipping analysis tool for research and blog posts
