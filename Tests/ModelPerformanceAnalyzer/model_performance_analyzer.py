#!/usr/bin/env python3
"""
Model Performance Analysis Tool

Combines description quality data with performance metrics (timing, tokens, costs)
to provide comprehensive insights into AI model performance for image description tasks.

This tool merges:
- combineddescriptions.csv (description content)
- workflow_timing_stats.csv (performance metrics)

And produces:
- Combined CSV with all metrics
- Markdown blog post with analysis
- Statistical insights and comparisons

Usage:
    python model_performance_analyzer.py
    python model_performance_analyzer.py --input-dir /path/to/analysis/results
    python model_performance_analyzer.py --input-dir /path/to/input --output-dir /path/to/output
"""

import csv
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Tuple
import json
from datetime import datetime
from collections import defaultdict


def load_descriptions(csv_path: Path) -> Dict[str, Dict[str, str]]:
    """
    Load descriptions from combineddescriptions.csv.
    
    Returns:
        Dict mapping model_name -> {image_name: description}
    """
    descriptions = {}
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        
        # Skip first two columns (Image Name, Prompt)
        model_columns = headers[2:]
        
        for row in reader:
            image_name = row['Image Name']
            
            for model in model_columns:
                if model not in descriptions:
                    descriptions[model] = {}
                
                desc = row.get(model, '').strip()
                if desc:
                    descriptions[model][image_name] = desc
    
    return descriptions


def load_performance_metrics(csv_path: Path) -> Dict[str, Dict]:
    """
    Load performance metrics from workflow_timing_stats.csv.
    
    Returns:
        Dict mapping model_name -> performance_metrics_dict
    """
    metrics = {}
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            workflow_name = row['Workflow']
            
            # Parse numeric fields with safety for empty values
            def safe_float(val, default=0.0):
                try:
                    return float(val) if val and val.strip() else default
                except ValueError:
                    return default
            
            def safe_int(val, default=0):
                try:
                    return int(val) if val and val.strip() else default
                except ValueError:
                    return default
            
            metrics[workflow_name] = {
                'provider': row['Provider'],
                'model': row['Model'],
                'prompt': row['Prompt'],
                'total_files': safe_int(row['Total Files in Workflow']),
                'duration_seconds': safe_float(row['Total Duration (seconds)']),
                'duration_minutes': safe_float(row['Total Duration (minutes)']),
                'avg_time_per_desc': safe_float(row['Avg Time/Description (seconds)']),
                'throughput': safe_float(row['Descriptions/Minute Throughput']),
                'total_tokens': safe_int(row['Total Tokens (Billable)']),
                'prompt_tokens': safe_int(row['Prompt Tokens (Input)']),
                'completion_tokens': safe_int(row['Completion Tokens (Output)']),
                'estimated_cost': safe_float(row['Estimated Cost ($)']),
            }
    
    return metrics


def analyze_description(description: str) -> Dict:
    """
    Analyze a description and extract quality metrics.
    
    Returns:
        Dict with word_count, char_count, sentence_count, etc.
    """
    if not description:
        return {
            'word_count': 0,
            'char_count': 0,
            'sentence_count': 0,
            'avg_word_length': 0.0
        }
    
    # Word count
    words = description.split()
    word_count = len(words)
    
    # Character count (excluding spaces)
    char_count = len(description.replace(' ', ''))
    
    # Sentence count (rough approximation)
    sentence_markers = ['. ', '! ', '? ']
    sentence_count = sum(description.count(marker) for marker in sentence_markers)
    if sentence_count == 0:
        sentence_count = 1  # At least one sentence
    
    # Average word length
    avg_word_length = char_count / word_count if word_count > 0 else 0
    
    return {
        'word_count': word_count,
        'char_count': char_count,
        'sentence_count': sentence_count,
        'avg_word_length': round(avg_word_length, 2)
    }


def combine_data(descriptions: Dict, metrics: Dict) -> List[Dict]:
    """
    Combine description and performance data into comprehensive records.
    
    Returns:
        List of dicts with all combined metrics
    """
    combined = []
    
    for model_name in descriptions.keys():
        # Get performance metrics for this model
        perf = metrics.get(model_name, {})
        
        # Get all descriptions for this model
        model_descriptions = descriptions[model_name]
        
        # Analyze each description
        for image_name, description in model_descriptions.items():
            desc_analysis = analyze_description(description)
            
            # Calculate cost efficiency metrics if we have cost data
            cost_per_word = 0.0
            if perf.get('estimated_cost', 0) > 0 and desc_analysis['word_count'] > 0:
                cost_per_word = perf['estimated_cost'] / desc_analysis['word_count']
            
            # Combine all data
            record = {
                'model_name': model_name,
                'image_name': image_name,
                'provider': perf.get('provider', ''),
                'model_id': perf.get('model', ''),
                'prompt_style': perf.get('prompt', ''),
                
                # Performance metrics
                'duration_seconds': perf.get('duration_seconds', 0),
                'throughput_per_min': perf.get('throughput', 0),
                
                # Token usage
                'total_tokens': perf.get('total_tokens', 0),
                'prompt_tokens': perf.get('prompt_tokens', 0),
                'completion_tokens': perf.get('completion_tokens', 0),
                
                # Cost metrics
                'estimated_cost': perf.get('estimated_cost', 0),
                'cost_per_word': round(cost_per_word, 6),
                
                # Description quality metrics
                'word_count': desc_analysis['word_count'],
                'char_count': desc_analysis['char_count'],
                'sentence_count': desc_analysis['sentence_count'],
                'avg_word_length': desc_analysis['avg_word_length'],
                
                # Full description
                'description': description
            }
            
            combined.append(record)
    
    return combined


def generate_comprehensive_csv(combined_data: List[Dict], output_path: Path):
    """Generate comprehensive CSV with all metrics."""
    
    if not combined_data:
        print("No data to write!")
        return
    
    fieldnames = [
        'model_name', 'provider', 'model_id', 'image_name', 'prompt_style',
        'duration_seconds', 'throughput_per_min', 
        'total_tokens', 'prompt_tokens', 'completion_tokens',
        'estimated_cost', 'cost_per_word',
        'word_count', 'char_count', 'sentence_count', 'avg_word_length',
        'description'
    ]
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(combined_data)
    
    print(f"[OK] Comprehensive CSV written to: {output_path}")


def generate_analysis_report(combined_data: List[Dict], output_path: Path):
    """Generate markdown blog post with analysis."""
    
    # Calculate rankings and insights
    cloud_models = [r for r in combined_data if r['provider'] in ['claude', 'openai']]
    local_models = [r for r in combined_data if r['provider'] == 'ollama']
    
    # Sort by various metrics
    by_speed = sorted(combined_data, key=lambda x: x['duration_seconds'] if x['duration_seconds'] > 0 else float('inf'))
    by_cost = sorted([r for r in combined_data if r['estimated_cost'] > 0], key=lambda x: x['estimated_cost'])
    by_detail = sorted(combined_data, key=lambda x: x['word_count'], reverse=True)
    by_efficiency = sorted([r for r in combined_data if r['cost_per_word'] > 0], key=lambda x: x['cost_per_word'])
    
    # Generate blog post content
    content = f"""# AI Vision Model Comparison: 26 Models, One Image, Comprehensive Analysis

*Generated on {datetime.now().strftime('%B %d, %Y')}*

## Executive Summary

We tested **{len(combined_data)} AI vision models** ({len(cloud_models)} cloud-based, {len(local_models)} local) on a single test image to compare their performance across multiple dimensions: speed, cost, description quality, and detail level.

**Key Findings:**
- **Fastest Model**: {by_speed[0]['model_name']} ({by_speed[0]['duration_seconds']:.2f}s)
- **Most Detailed**: {by_detail[0]['model_name']} ({by_detail[0]['word_count']} words)
- **Most Cost-Effective**: {by_efficiency[0]['model_name']} (${by_efficiency[0]['cost_per_word']:.6f}/word)
- **Cheapest Overall**: {by_cost[0]['model_name']} (${by_cost[0]['estimated_cost']:.4f})

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

**Cloud Models (n={len(cloud_models)}):**
- Average processing time: {sum(r['duration_seconds'] for r in cloud_models)/len(cloud_models):.2f}s
- Average description length: {sum(r['word_count'] for r in cloud_models)/len(cloud_models):.1f} words
- Average cost: ${sum(r['estimated_cost'] for r in cloud_models if r['estimated_cost'] > 0)/len([r for r in cloud_models if r['estimated_cost'] > 0]):.4f}

**Local Models (n={len(local_models)}):**
- Average processing time: {sum(r['duration_seconds'] for r in local_models if r['duration_seconds'] > 0)/len([r for r in local_models if r['duration_seconds'] > 0]):.2f}s
- Average description length: {sum(r['word_count'] for r in local_models)/len(local_models):.1f} words
- Cost: $0.00 (local processing)

## Top Performers by Category

### Speed Rankings (Fastest First)

| Rank | Model | Provider | Time (s) | Throughput/min |
|------|-------|----------|----------|----------------|
"""
    
    # Add top 10 fastest
    for i, record in enumerate(by_speed[:10], 1):
        content += f"| {i} | {record['model_name']} | {record['provider']} | {record['duration_seconds']:.2f} | {record['throughput_per_min']:.2f} |\n"
    
    content += """
### Detail Level Rankings (Most Detailed First)

| Rank | Model | Provider | Words | Characters | Sentences |
|------|-------|----------|-------|------------|-----------|
"""
    
    # Add top 10 most detailed
    for i, record in enumerate(by_detail[:10], 1):
        content += f"| {i} | {record['model_name']} | {record['provider']} | {record['word_count']} | {record['char_count']} | {record['sentence_count']} |\n"
    
    # Add cost analysis for cloud models
    if by_cost:
        content += """
### Cost Efficiency Rankings (Cloud Models Only)

| Rank | Model | Total Cost | Words | Cost/Word | Tokens |
|------|-------|------------|-------|-----------|--------|
"""
        
        for i, record in enumerate(by_efficiency[:10], 1):
            content += f"| {i} | {record['model_name']} | ${record['estimated_cost']:.4f} | {record['word_count']} | ${record['cost_per_word']:.6f} | {record['total_tokens']} |\n"
    
    content += """
## Detailed Analysis

### Speed vs Detail Trade-off

Analyzing the relationship between processing time and description detail reveals interesting patterns:

"""
    
    # Find examples of different trade-off strategies
    fast_and_detailed = [r for r in combined_data if r['duration_seconds'] > 0 and r['duration_seconds'] < 20 and r['word_count'] > 100]
    slow_but_detailed = [r for r in combined_data if r['duration_seconds'] > 100 and r['word_count'] > 100]
    fast_but_brief = [r for r in combined_data if r['duration_seconds'] > 0 and r['duration_seconds'] < 20 and r['word_count'] < 50]
    
    if fast_and_detailed:
        content += f"**Fast & Detailed Winners:** {', '.join(r['model_name'] for r in fast_and_detailed[:3])}\n"
        content += f"- These models provide detailed descriptions (100+ words) in under 20 seconds\n\n"
    
    if slow_but_detailed:
        content += f"**Thorough but Slow:** {', '.join(r['model_name'] for r in slow_but_detailed[:3])}\n"
        content += f"- Maximum detail but requires patience (100+ seconds)\n\n"
    
    if fast_but_brief:
        content += f"**Quick Snapshots:** {', '.join(r['model_name'] for r in fast_but_brief[:3])}\n"
        content += f"- Ultra-fast (< 20s) but concise descriptions (< 50 words)\n\n"
    
    content += """
### Provider-Specific Insights

#### Claude Models (Anthropic)
"""
    
    claude_models = [r for r in combined_data if r['provider'] == 'claude']
    if claude_models:
        avg_claude_time = sum(r['duration_seconds'] for r in claude_models) / len(claude_models)
        avg_claude_words = sum(r['word_count'] for r in claude_models) / len(claude_models)
        avg_claude_cost = sum(r['estimated_cost'] for r in claude_models if r['estimated_cost'] > 0) / len([r for r in claude_models if r['estimated_cost'] > 0])
        
        content += f"- **Count**: {len(claude_models)} models tested\n"
        content += f"- **Average Time**: {avg_claude_time:.2f}s\n"
        content += f"- **Average Detail**: {avg_claude_words:.1f} words\n"
        content += f"- **Average Cost**: ${avg_claude_cost:.4f}\n"
        content += f"- **Fastest**: {min(claude_models, key=lambda x: x['duration_seconds'])['model_name']}\n"
        content += f"- **Most Detailed**: {max(claude_models, key=lambda x: x['word_count'])['model_name']}\n\n"
    
    content += """#### OpenAI Models
"""
    
    openai_models = [r for r in combined_data if r['provider'] == 'openai']
    if openai_models:
        avg_openai_time = sum(r['duration_seconds'] for r in openai_models if r['duration_seconds'] > 0) / len([r for r in openai_models if r['duration_seconds'] > 0])
        avg_openai_words = sum(r['word_count'] for r in openai_models) / len(openai_models)
        avg_openai_cost = sum(r['estimated_cost'] for r in openai_models if r['estimated_cost'] > 0) / len([r for r in openai_models if r['estimated_cost'] > 0])
        
        content += f"- **Count**: {len(openai_models)} models tested\n"
        content += f"- **Average Time**: {avg_openai_time:.2f}s\n"
        content += f"- **Average Detail**: {avg_openai_words:.1f} words\n"
        content += f"- **Average Cost**: ${avg_openai_cost:.4f}\n\n"
    
    content += """#### Ollama Local Models
"""
    
    if local_models:
        models_with_time = [r for r in local_models if r['duration_seconds'] > 0]
        if models_with_time:
            avg_ollama_time = sum(r['duration_seconds'] for r in models_with_time) / len(models_with_time)
            avg_ollama_words = sum(r['word_count'] for r in local_models) / len(local_models)
            
            content += f"- **Count**: {len(local_models)} models tested\n"
            content += f"- **Average Time**: {avg_ollama_time:.2f}s\n"
            content += f"- **Average Detail**: {avg_ollama_words:.1f} words\n"
            content += f"- **Cost**: $0.00 (local processing, no API fees)\n"
            content += f"- **Fastest Local**: {min(models_with_time, key=lambda x: x['duration_seconds'])['model_name']}\n"
            content += f"- **Slowest Local**: {max(models_with_time, key=lambda x: x['duration_seconds'])['model_name']}\n\n"
    
    content += """
## Key Takeaways

### For Cost-Conscious Users
"""
    
    if by_cost and len(by_cost) > 0:
        cheapest = by_cost[0]
        content += f"- **Cheapest cloud option**: {cheapest['model_name']} at ${cheapest['estimated_cost']:.4f} per image\n"
        content += f"- **Best value**: {by_efficiency[0]['model_name']} at ${by_efficiency[0]['cost_per_word']:.6f} per word\n"
    content += f"- **Zero cost option**: Any Ollama model (free local processing)\n\n"
    
    content += """### For Speed-Critical Applications
"""
    
    if by_speed:
        content += f"- **Absolute fastest**: {by_speed[0]['model_name']} ({by_speed[0]['duration_seconds']:.2f}s)\n"
        fast_cloud = [r for r in by_speed if r['provider'] in ['claude', 'openai']]
        if fast_cloud:
            content += f"- **Fastest cloud**: {fast_cloud[0]['model_name']} ({fast_cloud[0]['duration_seconds']:.2f}s)\n"
        fast_local = [r for r in by_speed if r['provider'] == 'ollama']
        if fast_local:
            content += f"- **Fastest local**: {fast_local[0]['model_name']} ({fast_local[0]['duration_seconds']:.2f}s)\n\n"
    
    content += """### For Maximum Detail
"""
    
    if by_detail:
        content += f"- **Most comprehensive**: {by_detail[0]['model_name']} ({by_detail[0]['word_count']} words)\n"
        detailed_cloud = [r for r in by_detail if r['provider'] in ['claude', 'openai']]
        if detailed_cloud:
            content += f"- **Most detailed cloud**: {detailed_cloud[0]['model_name']} ({detailed_cloud[0]['word_count']} words)\n"
        detailed_local = [r for r in by_detail if r['provider'] == 'ollama']
        if detailed_local:
            content += f"- **Most detailed local**: {detailed_local[0]['model_name']} ({detailed_local[0]['word_count']} words)\n\n"
    
    content += """
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
"""
    
    # Write the report
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"[OK] Analysis report written to: {output_path}")


def main():
    """Main execution function."""
    
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Analyze AI vision model performance by combining description quality with metrics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use default paths (idtexternal/idt/analysis/results)
  python model_performance_analyzer.py
  
  # Specify custom input directory
  python model_performance_analyzer.py --input-dir /path/to/results
  
  # Specify both input and output directories
  python model_performance_analyzer.py --input-dir /path/to/input --output-dir /path/to/output
        """
    )
    
    # Set up default paths
    script_dir = Path(__file__).parent  # Tests/ModelPerformanceAnalyzer
    repo_root = script_dir.parent.parent  # Go up to repo root
    default_input_dir = repo_root / "idtexternal" / "idt" / "analysis" / "results"
    
    parser.add_argument(
        '--input-dir',
        type=Path,
        default=default_input_dir,
        help=f'Directory containing combineddescriptions.csv and workflow_timing_stats.csv (default: {default_input_dir})'
    )
    
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=script_dir,
        help=f'Directory where output files will be saved (default: {script_dir})'
    )
    
    args = parser.parse_args()
    
    # Use provided or default paths
    analysis_dir = args.input_dir
    output_dir = args.output_dir
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 70)
    print("AI Vision Model Performance Analysis Tool")
    print("=" * 70)
    print()
    print(f"Input directory:  {analysis_dir}")
    print(f"Output directory: {output_dir}")
    print()
    
    # Load data
    print("Loading data...")
    descriptions_file = analysis_dir / "combineddescriptions.csv"
    metrics_file = analysis_dir / "workflow_timing_stats.csv"
    
    if not descriptions_file.exists():
        print(f"ERROR: Descriptions file not found: {descriptions_file}")
        return 1
    
    if not metrics_file.exists():
        print(f"ERROR: Metrics file not found: {metrics_file}")
        return 1
    
    descriptions = load_descriptions(descriptions_file)
    print(f"  [OK] Loaded descriptions for {len(descriptions)} models")
    
    metrics = load_performance_metrics(metrics_file)
    print(f"  [OK] Loaded performance metrics for {len(metrics)} workflows")
    
    # Combine data
    print("\nCombining datasets...")
    combined_data = combine_data(descriptions, metrics)
    print(f"  [OK] Combined {len(combined_data)} records")
    
    # Generate outputs
    print("\nGenerating outputs...")
    
    csv_output = output_dir / "model_analysis_comprehensive.csv"
    generate_comprehensive_csv(combined_data, csv_output)
    
    blog_output = output_dir / "model_analysis_blog_post.md"
    generate_analysis_report(combined_data, blog_output)
    
    print("\n" + "=" * 70)
    print("Analysis Complete!")
    print("=" * 70)
    print(f"\nOutputs:")
    print(f"  1. Comprehensive CSV: {csv_output}")
    print(f"  2. Blog Post Analysis: {blog_output}")
    print()
    print("Summary Statistics:")
    print(f"  Total Models Analyzed: {len(set(r['model_name'] for r in combined_data))}")
    print(f"  Cloud Models: {len([r for r in combined_data if r['provider'] in ['claude', 'openai']])}")
    print(f"  Local Models: {len([r for r in combined_data if r['provider'] == 'ollama'])}")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
