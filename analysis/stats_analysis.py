#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyze statistics from multiple workflow runs.

This script extracts and analyzes performance metrics from workflow logs,
including timing data, throughput, and comparison across different AI providers.
"""

import argparse
import sys
import os
from pathlib import Path

# Add parent directory to path for resource manager import
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

try:
    from scripts.resource_manager import get_resource_path
except ImportError:
    # Fallback if resource manager not available
    def get_resource_path(relative_path):
        return Path(__file__).parent.parent / relative_path
import re
import statistics
import sys
import csv
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json
from analysis_utils import get_safe_filename, ensure_directory

# Fix Windows terminal encoding issues
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def extract_timestamp_from_log_line(line: str) -> Optional[str]:
    """
    Extract timestamp from log line, supporting both old and new formats.
    
    New format (screen reader friendly): INFO - Message - (2025-10-12 14:30:00)
    Old format: 2025-10-12 14:30:00 - module - INFO - Message
    
    Returns:
        Timestamp string in format 'YYYY-MM-DD HH:MM:SS' or None if not found
    """
    # Try new format first (timestamp at end in parentheses)
    new_format_match = re.search(r'\((\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\)', line)
    if new_format_match:
        return new_format_match.group(1)
    
    # Fall back to old format (timestamp at start)
    old_format_match = re.search(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
    if old_format_match:
        return old_format_match.group(1)
    
    return None


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
        'processing_times': [],  # Individual image processing times with filenames
        'average_time_per_image': None,
        'min_time': None,
        'max_time': None,
        'median_time': None,
        'min_time_file': None,  # NEW: filename with minimum time
        'max_time_file': None,  # NEW: filename with maximum time
        'completed_steps': [],
        'videos_found': 0,
        'frames_extracted': 0,
        'heic_files_found': 0,  # NEW: HEIC files found for conversion
        'heic_files_converted': 0,  # NEW: HEIC files successfully converted
        'conversion_duration': None,  # NEW: Time spent on HEIC conversion
        'errors': 0,
        'provider': None,
        'model': None,
        'prompt_style': None,  # NEW: Prompt style (narrative, detailed, concise, etc.)
        'total_tokens': None,  # NEW: Total tokens from API
        'prompt_tokens': None,  # NEW: Input/prompt tokens
        'completion_tokens': None,  # NEW: Output/completion tokens
        'estimated_cost': None,  # NEW: Cost in dollars
    }
    
    if not log_path.exists():
        print(f"Warning: {log_path} not found")
        return stats
    
    # Extract provider, model, and prompt_style from directory name
    # Format: wf_PROVIDER_MODEL_[VARIANT]_PROMPTSTYLE_DATETIME
    dir_name = log_path.parent.parent.name
    parts = dir_name.split('_')
    if len(parts) >= 3:
        stats['provider'] = parts[1]
        stats['model'] = parts[2]
        
        # Prompt style is typically in parts[3] or parts[4] (if model has variant)
        # Known prompt styles to look for
        prompt_styles = ['narrative', 'detailed', 'concise', 'technical', 'creative', 'colorful', 'artistic']
        for i in range(3, len(parts)):
            if parts[i] in prompt_styles:
                stats['prompt_style'] = parts[i]
                break
    
    # Track conversion times and current filename
    conversion_start = None
    conversion_end = None
    current_filename = None
    recent_lines = []  # Keep track of recent lines for filename extraction
    
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
            
            # Individual processing times with filenames
            elif 'Processing duration:' in line and '__main__' in line:
                match = re.search(r'Processing duration: ([\d.]+) seconds', line)
                if match:
                    processing_time = float(match.group(1))
                    # Look back through recent lines for "Generated description for"
                    filename = "Unknown"
                    for recent_line in reversed(recent_lines[-10:]):  # Check last 10 lines
                        filename_match = re.search(r'Generated description for (.+?)(?:\s+\(Provider:|\s*$)', recent_line)
                        if filename_match:
                            filename = filename_match.group(1).strip()
                            break
                    
                    stats['processing_times'].append({
                        'time': processing_time,
                        'file': filename
                    })
            
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
            
            # HEIC conversion - files found
            elif 'Found' in line and 'HEIC files' in line:
                match = re.search(r'Found (\d+) HEIC files', line)
                if match:
                    stats['heic_files_found'] = int(match.group(1))
            
            # HEIC conversion - start time
            elif 'Starting image conversion' in line:
                timestamp = extract_timestamp_from_log_line(line)
                if timestamp:
                    conversion_start = timestamp
            
            # HEIC conversion - successful conversions count
            elif 'Successful conversions:' in line:
                match = re.search(r'Successful conversions: (\d+)', line)
                if match:
                    stats['heic_files_converted'] = int(match.group(1))
            
            # HEIC conversion - also check final summary
            elif 'HEIC conversions:' in line:
                match = re.search(r'HEIC conversions: (\d+)', line)
                if match:
                    # Update if we didn't catch it earlier
                    if stats['heic_files_converted'] == 0:
                        stats['heic_files_converted'] = int(match.group(1))
                # Capture end time
                timestamp = extract_timestamp_from_log_line(line)
                if timestamp:
                    conversion_end = timestamp
            
            # HEIC conversion - image conversion completed
            elif 'Image conversion completed' in line:
                # Capture end time if we haven't already
                if not conversion_end:
                    timestamp = extract_timestamp_from_log_line(line)
                    if timestamp:
                        conversion_end = timestamp
            
            # HEIC conversion - no files found
            elif 'No HEIC files found' in line:
                stats['heic_files_found'] = 0
                stats['heic_files_converted'] = 0
            
            # Token usage summary (from image_describer logs)
            elif 'Total tokens:' in line:
                match = re.search(r'Total tokens: ([\d,]+)', line)
                if match:
                    stats['total_tokens'] = int(match.group(1).replace(',', ''))
            
            elif 'Prompt tokens:' in line:
                match = re.search(r'Prompt tokens: ([\d,]+)', line)
                if match:
                    stats['prompt_tokens'] = int(match.group(1).replace(',', ''))
            
            elif 'Completion tokens:' in line:
                match = re.search(r'Completion tokens: ([\d,]+)', line)
                if match:
                    stats['completion_tokens'] = int(match.group(1).replace(',', ''))
            
            elif 'Estimated cost:' in line:
                match = re.search(r'Estimated cost: \$([\d.]+)', line)
                if match:
                    stats['estimated_cost'] = float(match.group(1))
            
            # Errors
            elif 'ERROR' in line:
                stats['errors'] += 1
            
            # Keep track of recent lines for filename extraction
            recent_lines.append(line)
            if len(recent_lines) > 20:  # Keep last 20 lines
                recent_lines.pop(0)
    
    # Calculate conversion duration
    if conversion_start and conversion_end:
        try:
            start_dt = datetime.strptime(conversion_start, '%Y-%m-%d %H:%M:%S')
            end_dt = datetime.strptime(conversion_end, '%Y-%m-%d %H:%M:%S')
            stats['conversion_duration'] = (end_dt - start_dt).total_seconds()
        except:
            pass
    
    # Calculate min, max, median from individual processing times
    if stats['processing_times']:
        times_only = [item['time'] for item in stats['processing_times']]
        stats['min_time'] = min(times_only)
        stats['max_time'] = max(times_only)
        stats['median_time'] = statistics.median(times_only)
        
        # Find files with min and max times
        for item in stats['processing_times']:
            if item['time'] == stats['min_time']:
                stats['min_time_file'] = item['file']
            if item['time'] == stats['max_time']:
                stats['max_time_file'] = item['file']
        
        # If average wasn't in log, calculate it
        if stats['average_time_per_image'] is None:
            stats['average_time_per_image'] = statistics.mean(times_only)
    
    # Also check image_describer log for token usage data
    image_describer_logs = list(log_path.parent.glob("image_describer_*.log"))
    if image_describer_logs:
        describer_log = image_describer_logs[0]  # Use first one
        try:
            with open(describer_log, 'r', encoding='utf-8') as f:
                for line in f:
                    # Look for TOKEN USAGE SUMMARY section
                    if 'Total tokens:' in line:
                        match = re.search(r'Total tokens: ([\d,]+)', line)
                        if match:
                            stats['total_tokens'] = int(match.group(1).replace(',', ''))
                    elif 'Prompt tokens:' in line:
                        match = re.search(r'Prompt tokens: ([\d,]+)', line)
                        if match:
                            stats['prompt_tokens'] = int(match.group(1).replace(',', ''))
                    elif 'Completion tokens:' in line:
                        match = re.search(r'Completion tokens: ([\d,]+)', line)
                        if match:
                            stats['completion_tokens'] = int(match.group(1).replace(',', ''))
                    elif 'Estimated cost:' in line:
                        match = re.search(r'Estimated cost: \$([\d.]+)', line)
                        if match:
                            stats['estimated_cost'] = float(match.group(1))
        except Exception as e:
            print(f"Warning: Could not parse image_describer log: {e}")
    
    return stats


def get_workflow_label(workflow_dir_name: str) -> str:
    """
    Extract a readable label from the workflow directory name.
    Creates unique, distinguishable labels for all models.
    
    Examples:
        wf_claude_claude-3-haiku-20240307_... -> Claude Haiku 3
        wf_claude_claude-3-5-haiku-20241022_... -> Claude Haiku 3.5
        wf_ollama_llava_7b_... -> Ollama LLaVA 7B
        wf_ollama_llava_13b_... -> Ollama LLaVA 13B
        wf_openai_gpt-4o-mini_... -> OpenAI GPT-4o-mini
    """
    parts = workflow_dir_name.split('_')
    
    if len(parts) >= 3:
        provider = parts[1].capitalize()
        model_part = parts[2]
        
        # For models with size/variant in parts[3], include it
        variant = parts[3] if len(parts) > 3 and parts[3] not in ['narrative', 'detailed', 'concise'] else None
        
        # Create readable labels for Claude models
        if provider.lower() == 'claude':
            # claude-3-haiku-20240307 -> Haiku 3
            # claude-3-5-haiku-20241022 -> Haiku 3.5
            # claude-opus-4-1-20250805 -> Opus 4.1
            # claude-sonnet-4-5-20250929 -> Sonnet 4.5
            if 'haiku' in model_part:
                if '3-5' in model_part:
                    return "Claude Haiku 3.5"
                else:
                    return "Claude Haiku 3"
            elif 'sonnet' in model_part:
                if '4-5' in model_part:
                    return "Claude Sonnet 4.5"
                elif '3-7' in model_part:
                    return "Claude Sonnet 3.7"
                elif 'sonnet-4' in model_part:
                    return "Claude Sonnet 4"
                else:
                    return "Claude Sonnet"
            elif 'opus' in model_part:
                if '4-1' in model_part:
                    return "Claude Opus 4.1"
                elif 'opus-4-2' in model_part:
                    return "Claude Opus 4"
                else:
                    return "Claude Opus"
        
        # Create readable labels for Ollama models
        elif provider.lower() == 'ollama':
            # llava with variant (7b, 13b, 34b, latest)
            if 'llava' in model_part and variant:
                base = "LLaVA"
                if 'phi3' in model_part:
                    base = "LLaVA-Phi3"
                elif 'llama3' in model_part:
                    base = "LLaVA-Llama3"
                
                # Format variant nicely
                if variant == 'latest':
                    return f"Ollama {base}"
                elif variant.endswith('b'):  # 7b, 13b, 34b
                    return f"Ollama {base} {variant.upper()}"
                else:
                    return f"Ollama {base} {variant}"
            
            # llama3.2-vision with variant (11b, 90b, latest)
            elif 'llama3.2-vision' in model_part or 'llama3-2-vision' in model_part:
                if variant == 'latest':
                    return "Ollama Llama3.2-Vision"
                elif variant.endswith('b'):
                    return f"Ollama Llama3.2-Vision {variant.upper()}"
                else:
                    return f"Ollama Llama3.2-Vision {variant}"
            
            # Other Ollama models (moondream, bakllava, etc.)
            elif model_part == 'moondream':
                return "Ollama Moondream"
            elif model_part == 'bakllava':
                return "Ollama BakLLaVA"
            elif 'minicpm' in model_part:
                if variant and variant.endswith('b'):
                    return f"Ollama MiniCPM-V {variant.upper()}"
                else:
                    return "Ollama MiniCPM-V"
            elif model_part == 'cogvlm2':
                return "Ollama CogVLM2"
            elif model_part == 'internvl':
                return "Ollama InternVL"
            elif model_part == 'gemma3':
                return "Ollama Gemma3"
            elif 'mistral' in model_part:
                return "Ollama Mistral-Small 3.1"
            else:
                # Generic fallback for Ollama
                if variant and variant != 'latest':
                    return f"Ollama {model_part.title()} {variant}"
                else:
                    return f"Ollama {model_part.title()}"
        
        # OpenAI models
        elif provider.lower() == 'openai':
            # gpt-4o, gpt-4o-mini, gpt-5
            if 'gpt-4o-mini' in model_part:
                return "OpenAI GPT-4o-mini"
            elif 'gpt-4o' in model_part:
                return "OpenAI GPT-4o"
            elif 'gpt-5' in model_part:
                return "OpenAI GPT-5"
            else:
                return f"OpenAI {model_part.upper()}"
        
        # Generic fallback for any other providers
        else:
            if variant and variant != 'latest':
                return f"{provider} {model_part} {variant}"
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
    if stats['prompt_style']:
        print(f"Prompt: {stats['prompt_style']}")
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
    
    # NEW: HEIC conversion stats
    if stats['heic_files_found'] > 0:
        print(f"\n  HEIC Conversion:")
        print(f"    Files Found:           {stats['heic_files_found']}")
        print(f"    Files Converted:       {stats['heic_files_converted']}")
        if stats['conversion_duration']:
            print(f"    Conversion Time:       {format_duration(stats['conversion_duration'])}")
        # Calculate non-converted (excluding extracted frames)
        non_converted = stats['total_files_processed'] - stats['heic_files_converted'] - stats['frames_extracted']
        if non_converted > 0:
            print(f"    Already JPG/PNG:       {non_converted}")
    
    if stats['average_time_per_image']:
        print(f"\n  Description Generation:")
        print(f"    Average Time/Image:    {stats['average_time_per_image']:.2f}s")
    
    if stats['min_time'] is not None:
        min_display = f"{stats['min_time']:.2f}s"
        if stats['min_time_file']:
            min_display += f" ({stats['min_time_file']})"
        print(f"    Min Time:              {min_display}")
    
    if stats['max_time'] is not None:
        max_display = f"{stats['max_time']:.2f}s"
        if stats['max_time_file']:
            max_display += f" ({stats['max_time_file']})"
        print(f"    Max Time:              {max_display}")
    
    if stats['median_time'] is not None:
        print(f"    Median Time:           {stats['median_time']:.2f}s")
    
    if stats['processing_times']:
        print(f"    Samples:               {len(stats['processing_times']):,} images (excludes extracted frames)")
    
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
    print(f"{'Workflow':<30} {'Prompt':<12} {'Files':<8} {'Duration':<12} {'Avg/Image':<12} {'Min':<8} {'Max':<8} {'Median':<8}")
    print("-" * 115)
    
    # Rows
    for stats in valid_stats:
        label = get_workflow_label(stats['workflow_dir'])
        prompt = stats['prompt_style'] if stats['prompt_style'] else "N/A"
        files = f"{stats['total_files_processed']:,}" if stats['total_files_processed'] else "N/A"
        duration = format_duration(stats['total_duration_seconds']) if stats['total_duration_seconds'] else "N/A"
        avg = f"{stats['average_time_per_image']:.2f}s" if stats['average_time_per_image'] else "N/A"
        min_t = f"{stats['min_time']:.2f}s" if stats['min_time'] is not None else "N/A"
        max_t = f"{stats['max_time']:.2f}s" if stats['max_time'] is not None else "N/A"
        median = f"{stats['median_time']:.2f}s" if stats['median_time'] is not None else "N/A"
        
        print(f"{label:<30} {prompt:<12} {files:<8} {duration:<12} {avg:<12} {min_t:<8} {max_t:<8} {median:<8}")


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
        prompt = f"({stats['prompt_style']})" if stats['prompt_style'] else ""
        print(f"  {i}. {label:<30} {prompt:<12} {stats['average_time_per_image']:.2f}s/image")
    
    # Consistency ranking (smallest range between min and max)
    print("\n📊 Most Consistent Processing Time:")
    stats_with_range = [(s, s['max_time'] - s['min_time']) for s in valid_stats if s['min_time'] is not None]
    sorted_by_consistency = sorted(stats_with_range, key=lambda x: x[1])
    for i, (stats, range_val) in enumerate(sorted_by_consistency, 1):
        label = get_workflow_label(stats['workflow_dir'])
        prompt = f"({stats['prompt_style']})" if stats['prompt_style'] else ""
        print(f"  {i}. {label:<30} {prompt:<12} Range: {range_val:.2f}s (min: {stats['min_time']:.2f}s, max: {stats['max_time']:.2f}s)")
    
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
        prompt = f"({stats['prompt_style']})" if stats['prompt_style'] else ""
        print(f"  {i}. {label:<30} {prompt:<12} {throughput:.1f} images/minute")


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
        # Extract just the time values from the dict structure
        times = [item['time'] for item in stats['processing_times']]
        all_processing_times.extend(times)
    
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


def save_stats_csv(all_stats: List[Dict], output_file: Path):
    """Save timing statistics to CSV file for quality analysis."""
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Header row
        writer.writerow([
            'Workflow',
            'Provider',
            'Model',
            'Prompt',
            'Total Files in Workflow',
            'Total Duration (seconds)',
            'Total Duration (minutes)',
            'HEIC Files Found',
            'HEIC Files Converted',
            'Already JPG/PNG Files',
            'Conversion Time (seconds)',
            'Avg Time/Description (seconds)',
            'Min Time (seconds)',
            'Min Time File',
            'Max Time (seconds)',
            'Max Time File',
            'Median Time (seconds)',
            'Time Range (seconds)',
            'Std Deviation (seconds)',
            'Descriptions/Minute Throughput',
            'AI Descriptions Generated',
            'Videos Found',
            'Frames Extracted',
            'Errors',
            'Total Tokens (Billable)',
            'Prompt Tokens (Input)',
            'Completion Tokens (Output)',
            'Estimated Cost ($)'
        ])
        
        # Data rows
        for stats in all_stats:
            label = get_workflow_label(stats['workflow_dir'])
            
            # Calculate standard deviation if we have processing times
            std_dev = None
            if len(stats['processing_times']) > 1:
                # Extract just the time values from processing_times dicts
                times = [item['time'] for item in stats['processing_times']]
                std_dev = statistics.stdev(times)
            
            # Calculate time range
            time_range = None
            if stats['min_time'] is not None and stats['max_time'] is not None:
                time_range = stats['max_time'] - stats['min_time']
            
            # Calculate throughput
            throughput = None
            if stats['average_time_per_image']:
                throughput = 60 / stats['average_time_per_image']
            
            # Calculate non-HEIC images (already JPG/PNG, excluding extracted frames)
            non_heic = stats['total_files_processed'] - stats['heic_files_converted'] - stats['frames_extracted']
            
            writer.writerow([
                label,
                stats['provider'] or '',
                stats['model'] or '',
                stats['prompt_style'] or '',
                stats['total_files_processed'] or 0,
                f"{stats['total_duration_seconds']:.2f}" if stats['total_duration_seconds'] else '',
                f"{stats['total_duration_minutes']:.2f}" if stats['total_duration_minutes'] else '',
                stats['heic_files_found'] or 0,
                stats['heic_files_converted'] or 0,
                non_heic if non_heic > 0 else 0,
                f"{stats['conversion_duration']:.2f}" if stats['conversion_duration'] else '',
                f"{stats['average_time_per_image']:.2f}" if stats['average_time_per_image'] else '',
                f"{stats['min_time']:.2f}" if stats['min_time'] is not None else '',
                stats['min_time_file'] or '',
                f"{stats['max_time']:.2f}" if stats['max_time'] is not None else '',
                stats['max_time_file'] or '',
                f"{stats['median_time']:.2f}" if stats['median_time'] is not None else '',
                f"{time_range:.2f}" if time_range is not None else '',
                f"{std_dev:.2f}" if std_dev is not None else '',
                f"{throughput:.2f}" if throughput is not None else '',
                len(stats['processing_times']),
                stats['videos_found'] or 0,
                stats['frames_extracted'] or 0,
                stats['errors'] or 0,
                stats['total_tokens'] if stats['total_tokens'] is not None else '',
                stats['prompt_tokens'] if stats['prompt_tokens'] is not None else '',
                stats['completion_tokens'] if stats['completion_tokens'] is not None else '',
                f"{stats['estimated_cost']:.4f}" if stats['estimated_cost'] is not None else ''
            ])
    
    print(f"CSV statistics saved to: {output_file}")


def main():
    """Main function to analyze workflow statistics."""
    parser = argparse.ArgumentParser(
        description='Analyze performance statistics from workflow logs.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Analyze workflows in default Descriptions directory
  python analyze_workflow_stats.py
  
  # Analyze workflows in custom directory
  python analyze_workflow_stats.py --input-dir /path/to/workflows
  
  # Specify custom output filenames
  python analyze_workflow_stats.py --csv-output timing_stats.csv --json-output stats.json
  
  # Full custom usage
  python analyze_workflow_stats.py --input-dir /data/workflows --csv-output my_stats.csv
        '''
    )
    
    parser.add_argument(
        '--input-dir',
        type=Path,
        default=None,
        help='Directory containing workflow folders (default: ../Descriptions relative to script)'
    )
    
    parser.add_argument(
        '--csv-output',
        type=str,
        default='analysis/results/workflow_timing_stats.csv',
        help='CSV output filename (default: analysis/results/workflow_timing_stats.csv)'
    )
    
    parser.add_argument(
        '--json-output',
        type=str,
        default='workflow_statistics.json',
        help='JSON output filename (default: workflow_statistics.json). Saved in analysis/results/ directory.'
    )
    
    args = parser.parse_args()
    
    # Determine input directory
    if args.input_dir:
        base_dir = args.input_dir
    else:
        # Default to Descriptions directory in current working directory
        base_dir = Path.cwd() / "Descriptions"
    
    if not base_dir.exists():
        print(f"Error: Descriptions directory not found at: {base_dir}")
        print("\nPlease specify the correct directory with --input-dir")
        return 1
    
    workflow_dirs = sorted([d for d in base_dir.glob("wf_*") if d.is_dir()])
    
    if not workflow_dirs:
        print("No workflow directories found in Descriptions folder!")
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
    
    # Save to JSON and CSV - resolve to absolute paths
    json_output = Path(args.json_output).resolve()
    ensure_directory(json_output.parent)
    json_output = get_safe_filename(json_output)
    
    csv_output = Path(args.csv_output).resolve()
    ensure_directory(csv_output.parent)
    csv_output = get_safe_filename(csv_output)
    
    save_stats_json(all_stats, json_output)
    save_stats_csv(all_stats, csv_output)
    
    print("\n" + "=" * 80)
    print("Analysis complete!")
    print(f"CSV data for quality analysis: {csv_output}")
    print(f"JSON data saved to: {json_output}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
