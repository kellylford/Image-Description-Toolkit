#!/usr/bin/env python3
"""
List available workflow results and generate commands to view them.

This script scans a directory for workflow results and creates a CSV
listing all available workflows with metadata and viewer commands.
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from datetime import datetime


def find_workflow_directories(base_dir: Path) -> list:
    """Find all workflow result directories.
    
    Workflow directories are named like:
    wf_<name>_<provider>_<model>_<prompt>_<timestamp>
    
    Args:
        base_dir: Base directory to search for workflows
        
    Returns:
        List of (path, metadata_dict) tuples
    """
    if not base_dir.exists():
        return []
    
    workflows = []
    
    for item in base_dir.iterdir():
        if not item.is_dir():
            continue
            
        # Check if it looks like a workflow directory
        if not item.name.startswith('wf_'):
            continue
        
        # Try to load metadata
        metadata_file = item / 'workflow_metadata.json'
        metadata = {}
        
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            except Exception:
                pass
        
        # If no metadata, try to parse from directory name
        if not metadata:
            metadata = parse_directory_name(item.name)
        
        workflows.append((item, metadata))
    
    return workflows


def parse_directory_name(dir_name: str) -> dict:
    """Parse workflow metadata from directory name.
    
    Format: wf_<name>_<provider>_<model>_<prompt>_<timestamp>
    
    Args:
        dir_name: Directory name to parse
        
    Returns:
        Dictionary with parsed metadata
    """
    parts = dir_name.split('_')
    metadata = {
        'workflow_name': 'unknown',
        'provider': 'unknown',
        'model': 'unknown',
        'prompt_style': 'unknown',
        'timestamp': 'unknown'
    }
    
    if len(parts) < 3:
        return metadata
    
    # Skip 'wf' prefix
    parts = parts[1:]
    
    # Try to find timestamp (YYYYMMDD_HHMMSS format)
    timestamp_idx = -1
    for i, part in enumerate(parts):
        if len(part) == 8 and part.isdigit():
            timestamp_idx = i
            break
    
    if timestamp_idx > 0:
        # Everything before timestamp
        before_timestamp = parts[:timestamp_idx]
        
        # Last part before timestamp is prompt style
        if len(before_timestamp) >= 1:
            metadata['prompt_style'] = before_timestamp[-1]
        
        # Second to last is model (may be multiple parts)
        if len(before_timestamp) >= 2:
            # Find where provider ends (ollama, openai, claude)
            provider_idx = -1
            for i, part in enumerate(before_timestamp):
                if part.lower() in ['ollama', 'openai', 'claude']:
                    provider_idx = i
                    metadata['provider'] = part
                    break
            
            if provider_idx >= 0:
                # Workflow name is everything before provider
                if provider_idx > 0:
                    metadata['workflow_name'] = '_'.join(before_timestamp[:provider_idx])
                
                # Model is between provider and prompt
                if provider_idx + 1 < len(before_timestamp) - 1:
                    metadata['model'] = '_'.join(before_timestamp[provider_idx + 1:-1])
        
        # Timestamp
        if timestamp_idx < len(parts):
            metadata['timestamp'] = '_'.join(parts[timestamp_idx:])
    
    return metadata


def count_descriptions(workflow_dir: Path) -> int:
    """Count the number of description files in the workflow.
    
    Args:
        workflow_dir: Path to workflow directory
        
    Returns:
        Number of description files found
    """
    descriptions_dir = workflow_dir / 'descriptions'
    if not descriptions_dir.exists():
        return 0
    
    # Count .txt files
    count = 0
    for item in descriptions_dir.glob('**/*.txt'):
        if item.is_file():
            count += 1
    
    return count


def format_timestamp(timestamp_str: str) -> str:
    """Format timestamp string to human-readable format.
    
    Args:
        timestamp_str: Timestamp string (YYYYMMDD_HHMMSS)
        
    Returns:
        Formatted timestamp string
    """
    try:
        # Parse timestamp
        if '_' in timestamp_str:
            date_part, time_part = timestamp_str.split('_')[:2]
        else:
            date_part = timestamp_str[:8]
            time_part = timestamp_str[8:14] if len(timestamp_str) >= 14 else '000000'
        
        dt = datetime.strptime(f"{date_part}{time_part}", "%Y%m%d%H%M%S")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return timestamp_str


def generate_viewer_command(workflow_dir: Path, use_relative_path: bool = True) -> str:
    """Generate the viewer command for a workflow.
    
    Args:
        workflow_dir: Path to workflow directory
        use_relative_path: If True, use relative path from current directory
        
    Returns:
        Viewer command string
    """
    if use_relative_path:
        try:
            # Try to make it relative to current directory
            rel_path = workflow_dir.relative_to(Path.cwd())
            path_str = str(rel_path).replace('\\', '/')
        except ValueError:
            # Can't make relative, use absolute
            path_str = str(workflow_dir).replace('\\', '/')
    else:
        path_str = str(workflow_dir).replace('\\', '/')
    
    return f'idt viewer "{path_str}"'


def main():
    """Main function for results-list command."""
    parser = argparse.ArgumentParser(
        description="List available workflow results and generate viewer commands",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List results in default Descriptions directory
  idt results-list
  
  # List results in specific directory
  idt results-list --input-dir c:\\path\\to\\results
  
  # Save to custom output file
  idt results-list --output my_workflows.csv
  
  # Use absolute paths in viewer commands
  idt results-list --absolute-paths
        """
    )
    
    parser.add_argument(
        '--input-dir', '-i',
        default='Descriptions',
        help='Directory containing workflow results (default: Descriptions)'
    )
    
    parser.add_argument(
        '--output', '-o',
        default='workflow_results.csv',
        help='Output CSV file (default: workflow_results.csv)'
    )
    
    parser.add_argument(
        '--absolute-paths',
        action='store_true',
        help='Use absolute paths in viewer commands instead of relative'
    )
    
    parser.add_argument(
        '--sort-by',
        choices=['name', 'timestamp', 'provider', 'model'],
        default='timestamp',
        help='Sort results by field (default: timestamp)'
    )
    
    args = parser.parse_args()
    
    # Resolve input directory
    input_dir = Path(args.input_dir)
    if not input_dir.is_absolute():
        input_dir = Path.cwd() / input_dir
    
    print(f"Scanning for workflow results in: {input_dir}")
    
    if not input_dir.exists():
        print(f"Error: Directory does not exist: {input_dir}")
        return 1
    
    # Find all workflow directories
    workflows = find_workflow_directories(input_dir)
    
    if not workflows:
        print(f"No workflow results found in {input_dir}")
        return 0
    
    print(f"Found {len(workflows)} workflow(s)")
    
    # Prepare data for CSV
    rows = []
    for workflow_dir, metadata in workflows:
        desc_count = count_descriptions(workflow_dir)
        viewer_cmd = generate_viewer_command(workflow_dir, not args.absolute_paths)
        
        row = {
            'Name': metadata.get('workflow_name', 'unknown'),
            'Provider': metadata.get('provider', 'unknown'),
            'Model': metadata.get('model', 'unknown'),
            'Prompt': metadata.get('prompt_style', 'unknown'),
            'Descriptions': desc_count,
            'Timestamp': format_timestamp(metadata.get('timestamp', 'unknown')),
            'Viewer Command': viewer_cmd
        }
        rows.append(row)
    
    # Sort results
    sort_key_map = {
        'name': 'Name',
        'timestamp': 'Timestamp',
        'provider': 'Provider',
        'model': 'Model'
    }
    sort_key = sort_key_map.get(args.sort_by, 'Timestamp')
    rows.sort(key=lambda x: x[sort_key])
    
    # Write CSV
    output_file = Path(args.output)
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['Name', 'Provider', 'Model', 'Prompt', 'Descriptions', 'Timestamp', 'Viewer Command']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"\nResults written to: {output_file}")
    print(f"\nSummary:")
    print(f"  Total workflows: {len(rows)}")
    print(f"  Providers: {', '.join(sorted(set(r['Provider'] for r in rows)))}")
    print(f"  Models: {', '.join(sorted(set(r['Model'] for r in rows)))}")
    print(f"\nTo view a workflow, copy and paste the command from the 'Viewer Command' column.")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
