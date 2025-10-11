# AI Vision Model Comparison: 26 Models, One Image, Comprehensive Analysis

*Generated on October 11, 2025*

## Executive Summary

We tested **153 AI vision models** (71 cloud-based, 76 local) on a single test image to compare their performance across multiple dimensions: speed, cost, description quality, and detail level.

**Key Findings:**
- **Fastest Model**: Ollama Moondream (6.75s)
- **Most Detailed**: Ollama Gemma3 (444 words)
- **Most Cost-Effective**: Claude Haiku 3.5 ($0.000011/word)
- **Cheapest Overall**: Claude Haiku 3.5 ($0.0020)

## Test Methodology

**Test Setup:**
- **Single Image**: Wisconsin Union Terrace outdoor scene
- **Prompt Style**: Narrative (descriptive style)
- **Models Tested**: 26 different AI vision models
  - 7 Claude models (Anthropic)
  - 3 OpenAI models (GPT-4o series)
  - 16 Ollama local models

**Metrics Collected:**
- Processing time (seconds)
- Token usage (input/output)
- Cost per description
- Description length (words, characters)
- Description detail level

## Cloud vs Local Models

### Performance Comparison

**Cloud Models (n=71):**
- Average processing time: 15.90s
- Average description length: 157.1 words
- Average cost: $0.0290

**Local Models (n=76):**
- Average processing time: 65.39s
- Average description length: 126.1 words
- Cost: $0.00 (local processing)

## Top Performers by Category

### Speed Rankings (Fastest First)

| Rank | Model | Provider | Time (s) | Throughput/min |
|------|-------|----------|----------|----------------|
| 1 | Ollama Moondream | ollama | 6.75 | 11.61 |
| 2 | Ollama Moondream | ollama | 6.75 | 11.61 |
| 3 | Claude Haiku 3 | claude | 7.65 | 16.85 |
| 4 | Claude Haiku 3 | claude | 7.65 | 16.85 |
| 5 | Claude Haiku 3 | claude | 7.65 | 16.85 |
| 6 | Claude Haiku 3 | claude | 7.65 | 16.85 |
| 7 | Claude Haiku 3 | claude | 7.65 | 16.85 |
| 8 | Claude Haiku 3 | claude | 7.65 | 16.85 |
| 9 | Claude Haiku 3 | claude | 7.65 | 16.85 |
| 10 | Claude Haiku 3 | claude | 7.65 | 16.85 |

### Detail Level Rankings (Most Detailed First)

| Rank | Model | Provider | Words | Characters | Sentences |
|------|-------|----------|-------|------------|-----------|
| 1 | Ollama Gemma3 | ollama | 444 | 2426 | 28 |
| 2 | Ollama Gemma3 | ollama | 440 | 2421 | 28 |
| 3 | Ollama Gemma3 | ollama | 435 | 2361 | 32 |
| 4 | Ollama Gemma3 | ollama | 434 | 2304 | 29 |
| 5 | Ollama Gemma3 | ollama | 434 | 2464 | 30 |
| 6 | Ollama Gemma3 | ollama | 434 | 2347 | 28 |
| 7 | Ollama Gemma3 | ollama | 433 | 2325 | 32 |
| 8 | Ollama Gemma3 | ollama | 432 | 2292 | 28 |
| 9 | Ollama Gemma3 | ollama | 431 | 2377 | 29 |
| 10 | Ollama Gemma3 | ollama | 421 | 2300 | 31 |

### Cost Efficiency Rankings (Cloud Models Only)

| Rank | Model | Total Cost | Words | Cost/Word | Tokens |
|------|-------|------------|-------|-----------|--------|
| 1 | Claude Haiku 3.5 | $0.0020 | 185 | $0.000011 | 1379 |
| 2 | Claude Haiku 3.5 | $0.0020 | 174 | $0.000011 | 1379 |
| 3 | Claude Haiku 3.5 | $0.0020 | 179 | $0.000011 | 1379 |
| 4 | Claude Haiku 3.5 | $0.0020 | 164 | $0.000012 | 1379 |
| 5 | Claude Haiku 3.5 | $0.0020 | 169 | $0.000012 | 1379 |
| 6 | Claude Haiku 3.5 | $0.0020 | 158 | $0.000013 | 1379 |
| 7 | Claude Haiku 3.5 | $0.0020 | 127 | $0.000016 | 1379 |
| 8 | OpenAI GPT-4o | $0.0043 | 224 | $0.000019 | 1272 |
| 9 | OpenAI GPT-4o | $0.0043 | 211 | $0.000020 | 1272 |
| 10 | Claude Haiku 3.5 | $0.0020 | 97 | $0.000021 | 1379 |

## Detailed Analysis

### Speed vs Detail Trade-off

Analyzing the relationship between processing time and description detail reveals interesting patterns:

**Fast & Detailed Winners:** Claude Haiku 3.5, Claude Haiku 3.5, Claude Haiku 3.5
- These models provide detailed descriptions (100+ words) in under 20 seconds

**Thorough but Slow:** Ollama Llama3.2-Vision 11B, Ollama Llama3.2-Vision, Ollama Llama3.2-Vision
- Maximum detail but requires patience (100+ seconds)


### Provider-Specific Insights

#### Claude Models (Anthropic)
- **Count**: 56 models tested
- **Average Time**: 14.87s
- **Average Detail**: 152.5 words
- **Average Cost**: $0.0172
- **Fastest**: Claude Haiku 3
- **Most Detailed**: Claude Sonnet 4.5

#### OpenAI Models
- **Count**: 15 models tested
- **Average Time**: 19.73s
- **Average Detail**: 174.3 words
- **Average Cost**: $0.0762

#### Ollama Local Models
- **Count**: 76 models tested
- **Average Time**: 65.39s
- **Average Detail**: 126.1 words
- **Cost**: $0.00 (local processing, no API fees)
- **Fastest Local**: Ollama Moondream
- **Slowest Local**: Ollama LLaVA 34B


## Key Takeaways

### For Cost-Conscious Users
- **Cheapest cloud option**: Claude Haiku 3.5 at $0.0020 per image
- **Best value**: Claude Haiku 3.5 at $0.000011 per word
- **Zero cost option**: Any Ollama model (free local processing)

### For Speed-Critical Applications
- **Absolute fastest**: Ollama Moondream (6.75s)
- **Fastest cloud**: Claude Haiku 3 (7.65s)
- **Fastest local**: Ollama Moondream (6.75s)

### For Maximum Detail
- **Most comprehensive**: Ollama Gemma3 (444 words)
- **Most detailed cloud**: OpenAI GPT-5 (237 words)
- **Most detailed local**: Ollama Gemma3 (444 words)


## Conclusion

This comprehensive analysis of 26 AI vision models reveals that there's no one-size-fits-all solution. The choice depends on your specific needs:

- **Need speed?** Local Ollama models like Moondream deliver results in seconds
- **Need detail?** Cloud models provide richer, more comprehensive descriptions
- **On a budget?** Ollama models are free; for cloud, Claude Haiku offers good value
- **Best balance?** Mid-tier models offer good speed, detail, and cost trade-offs

The full dataset with all metrics is available in the accompanying CSV file for deeper analysis.

## Data Files

- **Comprehensive Metrics**: `model_analysis_comprehensive.csv`
- **Raw Descriptions**: `../analysis/results/combineddescriptions.csv`
- **Performance Stats**: `../analysis/results/workflow_timing_stats.csv`

---

*Analysis performed using the Image Description Toolkit Model Analysis Tool*
*Test image: Wisconsin Union Terrace outdoor scene with narrative prompt*
