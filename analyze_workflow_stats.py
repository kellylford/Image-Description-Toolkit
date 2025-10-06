#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyze statistics from multiple workflow runs.

This script extracts and analyzes performance metrics from workflow logs,
including timing data, throughput, and comparison across different AI providers.
"""

import re
import statistics
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json

# Fix Windows terminal encoding issues
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def parse_workflow_log(log_path: Path) -> Dict:
    """
    Parse a workflow log file and extract statistics.
    
    Returns:
        Dictionary containing workflow statistics
    """
    stats = {
        'workflow_dir': log_path.parent.parent.name,
        'log_file': log_path.name,
        'start_time': None,
        'end_time': None,
        'total_duration_seconds': None,
        'total_duration_minutes': None,
        'total_files_processed': 0,
        'processing_times': [],  # Individual image processing times
        'average_time_per_image': None,
        'min_time': None,
        'max_time': None,
        'median_time': None,
        'completed_steps': [],
        'videos_found': 0,
        'frames_extracted': 0,
        'errors': 0,
        'provider': None,
        'model': None,
    }
    
    if not log_path.exists():
        print(f"Warning: {log_path} not found")
        return stats
    
    # Extract provider and model from directory name
    dir_name = log_path.parent.parent.name
    parts = dir_name.split('_')
    if len(parts) >= 3:
        stats['provider'] = parts[1]
        stats['model'] = parts[2]
    
    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            # Start time
            if 'workflow_orchestrator - INFO - Start time:' in line:
                match = re.search(r'Start time: (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                if match:
                    stats['start_time'] = match.group(1)
            
            # End time
            elif 'workflow_orchestrator - INFO - End time:' in line:
                match = re.search(r'End time: (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                if match:
                    stats['end_time'] = match.group(1)
            
            # Total execution time
            elif 'Total execution time:' in line:
                match = re.search(r'Total execution time: ([\d.]+) seconds \(([\d.]+) minutes\)', line)
                if match:
                    stats['total_duration_seconds'] = float(match.group(1))
                    stats['total_duration_minutes'] = float(match.group(2))
            
            # Total files processed
            elif 'Total files processed:' in line:
                match = re.search(r'Total files processed: (\d+)', line)
                if match:
                    stats['total_files_processed'] = int(match.group(1))
            
            # Average time per image
            elif 'Average time per new image:' in line or 'Average time per image:' in line:
                match = re.search(r'Average time per (?:new )?image: ([\d.]+) seconds', line)
                if match:
                    stats['average_time_per_image'] = float(match.group(1))
            
            # Individual processing times
            elif 'Processing duration:' in line and '__main__' in line:
                match = re.search(r'Processing duration: ([\d.]+) seconds', line)
                if match:
                    stats['processing_times'].append(float(match.group(1)))
            
            # Completed steps
            elif 'Completed steps:' in line:
                match = re.search(r'Completed steps: (.+)$', line)
                if match:
                    steps_str = match.group(1).strip()
                    stats['completed_steps'] = [s.strip() for s in steps_str.split(',')]
            
            # Videos found
            elif 'Total video files found:' in line:
                match = re.search(r'Total video files found: (\d+)', line)
                if match:
                    stats['videos_found'] = int(match.group(1))
            
            # Frames extracted
            elif 'Total frames extracted:' in line:
                match = re.search(r'Total frames extracted: (\d+)', line)
                if match:
                    stats['frames_extracted'] = int(match.group(1))
            
            # Errors
            elif 'ERROR' in line:
                stats['errors'] += 1
    
    # Calculate min, max, median from individual processing times
    if stats['processing_times']:
        stats['min_time'] = min(stats['processing_times'])
        stats['max_time'] = max(stats['processing_times'])
        stats['median_time'] = statistics.median(stats['processing_times'])
        
        # If average wasn't in log, calculate it
        if stats['average_time_per_image'] is None:
            stats['average_time_per_image'] = statistics.mean(stats['processing_times'])
    
    return stats


def get_workflow_label(workflow_dir_name: str) -> str:
    """Extract a readable label from the workflow directory name."""
    parts = workflow_dir_name.split('_')
    
    if len(parts) >= 3:
        provider = parts[1].capitalize()
        model_part = parts[2]
        
        # Clean up common model names
        if 'haiku' in model_part.lower():
            return f"{provider} Haiku"
        elif 'sonnet' in model_part.lower():
            return f"{provider} Sonnet"
        elif 'gpt-4o-mini' in model_part.lower():
            return f"{provider} GPT-4o-mini"
        elif 'llava' in model_part.lower():
            return f"{provider} LLaVA"
        else:
            return f"{provider} {model_part}"
    
    return workflow_dir_name


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable format."""
    if seconds is None:
        return "N/A"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


def print_section_header(title: str):
    """Print a formatted section header."""
    print(f"\n{'=' * 80}")
    print(f"{title:^80}")
    print(f"{'=' * 80}\n")


def print_workflow_stats(stats: Dict):
    """Print statistics for a single workflow."""
    label = get_workflow_label(stats['workflow_dir'])
    
    print(f"\n{label}")
    print("-" * 80)
    
    if stats['start_time'] and stats['end_time']:
        print(f"  Start Time:              {stats['start_time']}")
        print(f"  End Time:                {stats['end_time']}")
    
    if stats['total_duration_seconds']:
        print(f"  Total Duration:          {format_duration(stats['total_duration_seconds'])} ({stats['total_duration_minutes']:.1f} minutes)")
    
    if stats['total_files_processed']:
        print(f"  Files Processed:         {stats['total_files_processed']:,}")
    
    if stats['videos_found']:
        print(f"  Videos Found:            {stats['videos_found']}")
    
    if stats['frames_extracted']:
        print(f"  Frames Extracted:        {stats['frames_extracted']}")
    
    if stats['average_time_per_image']:
        print(f"\n  Average Time/Image:      {stats['average_time_per_image']:.2f}s")
    
    if stats['min_time'] is not None:
        print(f"  Min Time:                {stats['min_time']:.2f}s")
    
    if stats['max_time'] is not None:
        print(f"  Max Time:                {stats['max_time']:.2f}s")
    
    if stats['median_time'] is not None:
        print(f"  Median Time:             {stats['median_time']:.2f}s")
    
    if stats['processing_times']:
        print(f"  Samples Analyzed:        {len(stats['processing_times']):,} processing times")
    
    if stats['errors']:
        print(f"  Errors Encountered:      {stats['errors']}")
    
    if stats['completed_steps']:
        print(f"  Completed Steps:         {', '.join(stats['completed_steps'])}")


def print_comparison_table(all_stats: List[Dict]):
    """Print a comparison table across all workflows."""
    print_section_header("COMPARISON TABLE")
    
    # Filter out workflows with no data
    valid_stats = [s for s in all_stats if s['total_files_processed'] > 0]
    
    if not valid_stats:
        print("No workflow data available.")
        return
    
    # Header
    print(f"{'Workflow':<25} {'Files':<8} {'Duration':<12} {'Avg/Image':<12} {'Min':<8} {'Max':<8} {'Median':<8}")
    print("-" * 100)
    
    # Rows
    for stats in valid_stats:
        label = get_workflow_label(stats['workflow_dir'])
        files = f"{stats['total_files_processed']:,}" if stats['total_files_processed'] else "N/A"
        duration = format_duration(stats['total_duration_seconds']) if stats['total_duration_seconds'] else "N/A"
        avg = f"{stats['average_time_per_image']:.2f}s" if stats['average_time_per_image'] else "N/A"
        min_t = f"{stats['min_time']:.2f}s" if stats['min_time'] is not None else "N/A"
        max_t = f"{stats['max_time']:.2f}s" if stats['max_time'] is not None else "N/A"
        median = f"{stats['median_time']:.2f}s" if stats['median_time'] is not None else "N/A"
        
        print(f"{label:<25} {files:<8} {duration:<12} {avg:<12} {min_t:<8} {max_t:<8} {median:<8}")


def print_rankings(all_stats: List[Dict]):
    """Print rankings by different metrics."""
    print_section_header("RANKINGS")
    
    # Filter valid stats
    valid_stats = [s for s in all_stats if s['average_time_per_image'] is not None]
    
    if not valid_stats:
        print("No timing data available for rankings.")
        return
    
    # Speed ranking (fastest first)
    print("🏆 Fastest Average Processing Time:")
    sorted_by_speed = sorted(valid_stats, key=lambda x: x['average_time_per_image'])
    for i, stats in enumerate(sorted_by_speed, 1):
        label = get_workflow_label(stats['workflow_dir'])
        print(f"  {i}. {label:<30} {stats['average_time_per_image']:.2f}s/image")
    
    # Consistency ranking (smallest range between min and max)
    print("\n📊 Most Consistent Processing Time:")
    stats_with_range = [(s, s['max_time'] - s['min_time']) for s in valid_stats if s['min_time'] is not None]
    sorted_by_consistency = sorted(stats_with_range, key=lambda x: x[1])
    for i, (stats, range_val) in enumerate(sorted_by_consistency, 1):
        label = get_workflow_label(stats['workflow_dir'])
        print(f"  {i}. {label:<30} Range: {range_val:.2f}s (min: {stats['min_time']:.2f}s, max: {stats['max_time']:.2f}s)")
    
    # Throughput ranking (images per minute)
    print("\n⚡ Highest Throughput (images/minute):")
    throughput_list = []
    for stats in valid_stats:
        if stats['average_time_per_image']:
            throughput = 60 / stats['average_time_per_image']
            throughput_list.append((stats, throughput))
    
    sorted_by_throughput = sorted(throughput_list, key=lambda x: x[1], reverse=True)
    for i, (stats, throughput) in enumerate(sorted_by_throughput, 1):
        label = get_workflow_label(stats['workflow_dir'])
        print(f"  {i}. {label:<30} {throughput:.1f} images/minute")


def calculate_aggregate_stats(all_stats: List[Dict]):
    """Calculate aggregate statistics across all workflows."""
    print_section_header("AGGREGATE STATISTICS")
    
    valid_stats = [s for s in all_stats if s['total_files_processed'] > 0]
    
    if not valid_stats:
        print("No data available.")
        return
    
    total_files = sum(s['total_files_processed'] for s in valid_stats)
    total_duration = sum(s['total_duration_seconds'] for s in valid_stats if s['total_duration_seconds'])
    total_videos = sum(s['videos_found'] for s in valid_stats)
    total_frames = sum(s['frames_extracted'] for s in valid_stats)
    
    print(f"Total Files Processed Across All Workflows: {total_files:,}")
    print(f"Total Processing Time: {format_duration(total_duration)} ({total_duration / 3600:.1f} hours)")
    print(f"Total Videos Processed: {total_videos}")
    print(f"Total Frames Extracted: {total_frames:,}")
    
    # Average of averages
    avg_times = [s['average_time_per_image'] for s in valid_stats if s['average_time_per_image']]
    if avg_times:
        overall_avg = statistics.mean(avg_times)
        print(f"\nOverall Average Time per Image (across all providers): {overall_avg:.2f}s")
        print(f"Overall Images per Minute (average): {60/overall_avg:.1f} images/minute")
    
    # All processing times combined
    all_processing_times = []
    for stats in valid_stats:
        all_processing_times.extend(stats['processing_times'])
    
    if all_processing_times:
        print(f"\nCombined Statistics from {len(all_processing_times):,} individual image processing times:")
        print(f"  Mean:     {statistics.mean(all_processing_times):.2f}s")
        print(f"  Median:   {statistics.median(all_processing_times):.2f}s")
        print(f"  Min:      {min(all_processing_times):.2f}s")
        print(f"  Max:      {max(all_processing_times):.2f}s")
        print(f"  Std Dev:  {statistics.stdev(all_processing_times):.2f}s")


def save_stats_json(all_stats: List[Dict], output_file: Path):
    """Save statistics to JSON file for later analysis."""
    # Convert stats to JSON-serializable format
    json_data = {
        'generated_at': datetime.now().isoformat(),
        'workflows': all_stats
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2)
    
    print(f"\nDetailed statistics saved to: {output_file}")


def main():
    """Main function to analyze workflow statistics."""
    
    # Find all workflow directories
    base_dir = Path(__file__).parent
    workflow_dirs = sorted([d for d in base_dir.glob("wf_*") if d.is_dir()])
    
    if not workflow_dirs:
        print("No workflow directories found!")
        return
    
    print_section_header("WORKFLOW STATISTICS ANALYZER")
    print(f"Found {len(workflow_dirs)} workflow directories\n")
    
    # Parse all workflow logs
    all_stats = []
    
    for workflow_dir in workflow_dirs:
        # Find the workflow log file
        log_files = list((workflow_dir / "logs").glob("workflow_*.log"))
        
        if log_files:
            # Use the first (or only) workflow log
            log_file = log_files[0]
            print(f"Analyzing: {workflow_dir.name}")
            stats = parse_workflow_log(log_file)
            all_stats.append(stats)
        else:
            print(f"Warning: No workflow log found in {workflow_dir.name}")
    
    # Print individual workflow stats
    print_section_header("INDIVIDUAL WORKFLOW STATISTICS")
    for stats in all_stats:
        print_workflow_stats(stats)
    
    # Print comparison table
    print_comparison_table(all_stats)
    
    # Print rankings
    print_rankings(all_stats)
    
    # Print aggregate stats
    calculate_aggregate_stats(all_stats)
    
    # Save to JSON
    json_output = base_dir / "workflow_statistics.json"
    save_stats_json(all_stats, json_output)
    
    print("\n" + "=" * 80)
    print("Analysis complete!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
