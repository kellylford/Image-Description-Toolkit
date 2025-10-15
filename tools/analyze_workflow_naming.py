#!/usr/bin/env python3
"""
Analyze existing workflow directories and propose new names with image path identifiers.

This script examines workflow logs to extract input directories and proposes enhanced
directory names that include a unique portion of the image path for better identification.
"""

import os
import re
import csv
from pathlib import Path
from collections import defaultdict


def extract_input_dir_from_log(workflow_dir):
    """Extract input directory from workflow log file."""
    log_dir = workflow_dir / "logs"
    if not log_dir.exists():
        return None
    
    # Find workflow log file
    workflow_logs = list(log_dir.glob("workflow_*.log"))
    if not workflow_logs:
        return None
    
    # Read the first (usually only) workflow log
    log_file = workflow_logs[0]
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                # Look for "Input directory: " line
                match = re.search(r'Input directory:\s+(.+)', line)
                if match:
                    input_dir = match.group(1).strip()
                    return input_dir
    except Exception as e:
        print(f"Error reading {log_file}: {e}")
        return None
    
    return None


def get_unique_path_suffix(full_path, min_components=1, max_components=4):
    """
    Extract a unique suffix from the path starting from the right edge.
    
    Args:
        full_path: Full input directory path
        min_components: Minimum number of path components to include
        max_components: Maximum number of path components to include
    
    Returns:
        String with path components joined by underscores
    """
    # Normalize path separators
    full_path = full_path.replace('\\', '/').strip('/')
    
    # Split into components
    components = full_path.split('/')
    
    # Remove empty components
    components = [c for c in components if c]
    
    # Take the last N components (starting from right)
    # Start with min_components, could expand later if needed for uniqueness
    suffix_components = components[-min_components:] if len(components) >= min_components else components
    
    # Join with underscores and clean up
    suffix = '_'.join(suffix_components)
    
    # Clean up for use in directory name
    # Remove special characters, keep alphanumeric and basic punctuation
    suffix = re.sub(r'[^\w\-]', '_', suffix)
    
    # Remove multiple underscores
    suffix = re.sub(r'_+', '_', suffix)
    
    # Limit length
    if len(suffix) > 50:
        suffix = suffix[:50]
    
    return suffix.lower()


def parse_workflow_dirname(dirname):
    """
    Parse workflow directory name into components.
    
    Expected format: wf_PROVIDER_MODEL_PROMPT_TIMESTAMP
    Example: wf_claude_claude-3-haiku-20240307_narrative_20251011_103631
    
    Returns:
        dict with 'prefix', 'provider', 'model', 'prompt', 'timestamp', 'rest'
    """
    parts = dirname.split('_')
    
    if len(parts) < 2 or parts[0] != 'wf':
        return None
    
    # Try to identify timestamp (YYYYMMDD_HHMMSS format)
    timestamp_idx = None
    for i in range(len(parts) - 1, -1, -1):
        if re.match(r'^\d{8}$', parts[i]) and i + 1 < len(parts) and re.match(r'^\d{6}$', parts[i + 1]):
            timestamp_idx = i
            break
    
    if timestamp_idx is None or timestamp_idx < 3:
        # Can't parse reliably
        return {
            'prefix': 'wf',
            'provider': '',
            'model': '',
            'prompt': '',
            'timestamp': '',
            'rest': '_'.join(parts[1:])
        }
    
    # Everything before timestamp
    before_timestamp = parts[1:timestamp_idx]
    timestamp = '_'.join(parts[timestamp_idx:timestamp_idx+2])
    
    # Try to identify prompt style (last component before timestamp)
    prompt_style = before_timestamp[-1] if before_timestamp else ''
    
    # Provider and model are everything before prompt
    provider_model = before_timestamp[:-1] if len(before_timestamp) > 1 else before_timestamp
    
    provider = provider_model[0] if provider_model else ''
    model = '_'.join(provider_model[1:]) if len(provider_model) > 1 else ''
    
    return {
        'prefix': 'wf',
        'provider': provider,
        'model': model,
        'prompt': prompt_style,
        'timestamp': timestamp,
        'rest': '_'.join(before_timestamp)
    }


def generate_new_name_with_path(old_name, input_dir, min_components=1):
    """
    Generate new workflow directory name with input path identifier.
    
    New format: wf_PATH_IDENTIFIER_PROVIDER_MODEL_PROMPT_TIMESTAMP
    Example: wf_2025_07_claude_claude-3-haiku-20240307_narrative_20251011_103631
    """
    if not input_dir:
        return None
    
    # Get unique path suffix
    path_suffix = get_unique_path_suffix(input_dir, min_components=min_components)
    
    # Parse old name
    parsed = parse_workflow_dirname(old_name)
    if not parsed:
        return None
    
    # Construct new name: wf_PATH_PROVIDER_MODEL_PROMPT_TIMESTAMP
    new_name = f"wf_{path_suffix}_{parsed['rest']}_{parsed['timestamp']}"
    
    return new_name


def analyze_workflows(hold_dir, output_csv):
    """
    Analyze all workflows in hold directory and generate naming proposals.
    
    Args:
        hold_dir: Path to directory containing workflow directories
        output_csv: Path to output CSV file
    """
    results = []
    
    hold_path = Path(hold_dir)
    if not hold_path.exists():
        print(f"Error: Directory not found: {hold_dir}")
        return
    
    # Get all workflow directories
    workflow_dirs = [d for d in hold_path.iterdir() if d.is_dir() and d.name.startswith('wf_')]
    
    print(f"Found {len(workflow_dirs)} workflow directories")
    print("Analyzing...")
    
    # Track input directories to identify duplicates
    input_dir_counts = defaultdict(list)
    
    for wf_dir in sorted(workflow_dirs):
        old_name = wf_dir.name
        
        # Extract input directory from log
        input_dir = extract_input_dir_from_log(wf_dir)
        
        if input_dir:
            input_dir_counts[input_dir].append(old_name)
        
        # Generate new name with 1 component
        new_name_1comp = generate_new_name_with_path(old_name, input_dir, min_components=1)
        
        # Generate new name with 2 components
        new_name_2comp = generate_new_name_with_path(old_name, input_dir, min_components=2)
        
        # Generate new name with 3 components
        new_name_3comp = generate_new_name_with_path(old_name, input_dir, min_components=3)
        
        results.append({
            'old_name': old_name,
            'input_directory': input_dir or 'NOT_FOUND',
            'new_name_1_component': new_name_1comp or 'PARSE_ERROR',
            'new_name_2_components': new_name_2comp or 'PARSE_ERROR',
            'new_name_3_components': new_name_3comp or 'PARSE_ERROR',
        })
    
    # Write CSV
    print(f"\nWriting results to: {output_csv}")
    
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        fieldnames = [
            'old_name',
            'input_directory',
            'new_name_1_component',
            'new_name_2_components',
            'new_name_3_components',
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    
    # Print summary
    print(f"\nAnalysis complete!")
    print(f"Total workflows: {len(results)}")
    print(f"Logs found: {sum(1 for r in results if r['input_directory'] != 'NOT_FOUND')}")
    print(f"Logs missing: {sum(1 for r in results if r['input_directory'] == 'NOT_FOUND')}")
    
    # Show duplicate input directories
    print(f"\n=== Input Directory Usage ===")
    print(f"Unique input directories: {len(input_dir_counts)}")
    
    duplicates = {k: v for k, v in input_dir_counts.items() if len(v) > 1}
    if duplicates:
        print(f"\nInput directories used in multiple workflows: {len(duplicates)}")
        for input_dir, workflows in sorted(duplicates.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
            print(f"  {input_dir}")
            print(f"    Used in {len(workflows)} workflows:")
            for wf in workflows[:5]:  # Show first 5
                print(f"      - {wf}")
            if len(workflows) > 5:
                print(f"      ... and {len(workflows) - 5} more")
    
    print(f"\nResults saved to: {output_csv}")


if __name__ == "__main__":
    import sys
    import os
    
    # Default paths (user-agnostic)
    default_hold_dir = os.path.join(os.path.expanduser("~"), "idt", "descriptions", "hold")
    default_output = "workflow_naming_analysis.csv"  # Current directory
    
    hold_dir = sys.argv[1] if len(sys.argv) > 1 else default_hold_dir
    output_csv = sys.argv[2] if len(sys.argv) > 2 else default_output
    
    analyze_workflows(hold_dir, output_csv)
