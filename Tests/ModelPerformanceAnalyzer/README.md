# Model Performance Analyzer

A comprehensive analysis tool for comparing AI vision model performance across multiple dimensions: speed, cost, and description quality.

## Purpose

This tool combines workflow execution data (timing, tokens, costs) with generated descriptions to provide insights into the performance characteristics of different AI vision models. It's particularly useful for:

- Comparing cloud vs local model performance
- Identifying the best model for specific use cases (speed, cost, detail)
- Understanding trade-offs between different model choices
- Generating comparative analysis reports

## Files

- **model_performance_analyzer.py** - Main analysis script
- **model_analysis_comprehensive.csv** - Generated comprehensive metrics (all models with all data points)
- **model_analysis_blog_post.md** - Generated analysis report with insights and rankings

## Usage

### Quick Start

```bash
# Navigate to repository root
cd /path/to/idt

# Step 1: Combine all workflow descriptions (required first time or after new runs)
python analysis/combine_workflow_descriptions.py \
  --input-dir idtexternal/idt/Descriptions \
  --output idtexternal/idt/analysis/results/combineddescriptions.csv

# Step 2: Run the model performance analyzer
python Tests/ModelPerformanceAnalyzer/model_performance_analyzer.py
```

### When to Run Step 1 (Combine Descriptions)

You need to regenerate the combined descriptions CSV when:
- You've completed new workflow runs
- You've added new models
- The `combineddescriptions.csv` is missing or outdated
- You want to include more images in the analysis

**Note**: Step 1 can take a few minutes with 100+ workflow runs. You only need to run it when your workflow data changes.

## Input Data Sources

The analyzer reads from:
- `analysis/results/combineddescriptions.csv` - Model-generated descriptions
- `analysis/results/workflow_timing_stats.csv` - Execution timing, token counts, and costs

## Output

The tool generates two files in the `Tests/ModelPerformanceAnalyzer` directory:

1. **model_analysis_comprehensive.csv** - Complete dataset with calculated metrics:
   - Basic info: Model name, workflow name, provider
   - Performance: Execution time, tokens used, cost
   - Quality: Word count, character count, sentence count, average word length
   - Derived: Cost per word, speed ranking, detail ranking

2. **model_analysis_blog_post.md** - Markdown report with:
   - Executive summary of key findings
   - Methodology explanation
   - Cloud vs Local comparison
   - Speed rankings (top 10)
   - Detail level rankings (top 10)
   - Cost efficiency rankings
   - Provider-specific insights (Claude, OpenAI, Ollama)
   - Practical recommendations

## Key Metrics Calculated

- **Word Count** - Number of words in description
- **Cost per Word** - Total cost divided by word count (cloud models only)
- **Speed Ranking** - Relative speed compared to all models
- **Detail Ranking** - Relative detail level compared to all models
- **Average Word Length** - Average characters per word
- **Sentence Count** - Number of sentences in description

## Example Insights

### Latest Analysis (153 workflow runs, multiple images)
- **Fastest**: Ollama Moondream (6.75s)
- **Most Detailed**: Ollama Gemma3 (444 words)
- **Most Cost-Effective**: Claude Haiku 3.5 ($0.000011/word)
- **Cloud Average**: 15.90s, 157.1 words, $0.0290
- **Local Average**: 65.39s, 126.1 words, $0.00

### Original Single-Image Test (26 models, 1 image)
- **Fastest**: Ollama Moondream (6.75s)
- **Most Detailed**: Ollama Llama3.2-Vision 11B (264 words)
- **Most Cost-Effective**: Claude Haiku 3.5 ($0.000018/word)
- **Cloud Average**: 14.27s, 142.7 words, $0.0264
- **Local Average**: 86.35s, 168.4 words, $0.00

## Analysis Focus

The tool helps answer questions like:
- Which model is fastest for my use case?
- What's the most cost-effective cloud option?
- Which local model provides the best detail?
- How do cloud and local models compare?
- What are the trade-offs between speed, cost, and quality?

## Non-Shipping Tool

This is an analysis tool located in the `Tests/` directory and is not included in the distributed executable. It's for development, testing, and research purposes only.
