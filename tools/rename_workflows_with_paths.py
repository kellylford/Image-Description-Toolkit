#!/usr/bin/env python3
"""
Rename existing workflow directories to include 2-component path identifiers.

This script renames workflow directories from the current format:
    wf_PROVIDER_MODEL_PROMPT_TIMESTAMP
to the new format with 2-component path identifier:
    wf_PATH1_PATH2_PROVIDER_MODEL_PROMPT_TIMESTAMP

Example:
    Old: wf_claude_claude-3-haiku-20240307_narrative_20251011_103631
    New: wf_2025_07_claude_claude-3-haiku-20240307_narrative_20251011_103631

WARNING: This script performs file system operations. Make sure you have backups!

Usage:
    python rename_workflows_with_paths.py <hold_directory> [--dry-run]
    
    --dry-run: Show what would be renamed without actually renaming
"""

import os
import sys
import re
from pathlib import Path
import argparse


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


def get_path_identifier_2_components(full_path):
    """
    Extract 2-component path identifier from the input directory path.
    
    Args:
        full_path: Full input directory path
    
    Returns:
        String with 2 path components joined by underscores
    """
    # Normalize path separators
    full_path = full_path.replace('\\', '/').strip('/')
    
    # Split into components
    components = full_path.split('/')
    
    # Remove empty components
    components = [c for c in components if c]
    
    # Take the last 2 components
    suffix_components = components[-2:] if len(components) >= 2 else components
    
    # Join with underscores and clean up
    suffix = '_'.join(suffix_components)
    
    # Clean up for use in directory name
    # Remove special characters, keep alphanumeric and basic punctuation
    suffix = re.sub(r'[^\w\-]', '_', suffix)
    
    # Remove multiple underscores
    suffix = re.sub(r'_+', '_', suffix)
    
    # Limit length to avoid excessively long names
    if len(suffix) > 50:
        suffix = suffix[:50]
    
    return suffix.lower()


def parse_workflow_dirname(dirname):
    """
    Parse workflow directory name into components.
    
    Expected format: wf_PROVIDER_MODEL_PROMPT_TIMESTAMP
    Example: wf_claude_claude-3-haiku-20240307_narrative_20251011_103631
    
    Returns:
        dict with 'prefix', 'middle', 'timestamp'
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
    
    if timestamp_idx is None or timestamp_idx < 2:
        # Can't parse reliably
        return None
    
    # Everything before timestamp
    middle = '_'.join(parts[1:timestamp_idx])
    timestamp = '_'.join(parts[timestamp_idx:timestamp_idx+2])
    
    return {
        'prefix': 'wf',
        'middle': middle,
        'timestamp': timestamp
    }


def generate_new_name(old_name, input_dir):
    """
    Generate new workflow directory name with 2-component path identifier.
    
    New format: wf_PATH1_PATH2_PROVIDER_MODEL_PROMPT_TIMESTAMP
    """
    if not input_dir:
        return None
    
    # Get 2-component path identifier
    path_id = get_path_identifier_2_components(input_dir)
    
    # Parse old name
    parsed = parse_workflow_dirname(old_name)
    if not parsed:
        return None
    
    # Construct new name: wf_PATH_MIDDLE_TIMESTAMP
    new_name = f"{parsed['prefix']}_{path_id}_{parsed['middle']}_{parsed['timestamp']}"
    
    return new_name


def rename_workflows(hold_dir, dry_run=True):
    """
    Rename all workflow directories in the hold directory.
    
    Args:
        hold_dir: Path to directory containing workflow directories
        dry_run: If True, only show what would be renamed without actually renaming
    """
    hold_path = Path(hold_dir)
    if not hold_path.exists():
        print(f"Error: Directory not found: {hold_dir}")
        return
    
    # Get all workflow directories
    workflow_dirs = [d for d in hold_path.iterdir() if d.is_dir() and d.name.startswith('wf_')]
    
    print(f"{'='*80}")
    print(f"Workflow Directory Renaming Tool")
    print(f"{'='*80}")
    print(f"Mode: {'DRY RUN (no changes will be made)' if dry_run else 'LIVE (directories will be renamed)'}")
    print(f"Directory: {hold_dir}")
    print(f"Found {len(workflow_dirs)} workflow directories")
    print(f"{'='*80}\n")
    
    if not dry_run:
        response = input("This will rename directories. Are you sure you want to continue? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted.")
            return
        print()
    
    # Track results
    renamed_count = 0
    skipped_no_log = 0
    skipped_parse_error = 0
    skipped_already_exists = 0
    errors = []
    
    for wf_dir in sorted(workflow_dirs):
        old_name = wf_dir.name
        
        # Extract input directory from log
        input_dir = extract_input_dir_from_log(wf_dir)
        
        if not input_dir:
            print(f"SKIP (no log): {old_name}")
            skipped_no_log += 1
            continue
        
        # Generate new name
        new_name = generate_new_name(old_name, input_dir)
        
        if not new_name:
            print(f"SKIP (parse error): {old_name}")
            skipped_parse_error += 1
            continue
        
        # Check if already renamed (new name == old name)
        if new_name == old_name:
            # Already has the new format, skip
            continue
        
        # Check if new directory already exists
        new_path = hold_path / new_name
        if new_path.exists():
            print(f"SKIP (target exists): {old_name}")
            print(f"  Target: {new_name}")
            skipped_already_exists += 1
            continue
        
        # Show rename operation
        if dry_run:
            print(f"WOULD RENAME:")
        else:
            print(f"RENAMING:")
        
        print(f"  Old: {old_name}")
        print(f"  New: {new_name}")
        print(f"  Input dir: {input_dir}")
        
        # Perform rename if not dry run
        if not dry_run:
            try:
                wf_dir.rename(new_path)
                print(f"  ✓ Success")
                renamed_count += 1
            except Exception as e:
                print(f"  ✗ Error: {e}")
                errors.append((old_name, str(e)))
        else:
            renamed_count += 1
        
        print()
    
    # Print summary
    print(f"{'='*80}")
    print(f"Summary")
    print(f"{'='*80}")
    print(f"Total workflows found: {len(workflow_dirs)}")
    print(f"Renamed: {renamed_count}")
    print(f"Skipped (no log): {skipped_no_log}")
    print(f"Skipped (parse error): {skipped_parse_error}")
    print(f"Skipped (target exists): {skipped_already_exists}")
    
    if errors:
        print(f"\nErrors: {len(errors)}")
        for old_name, error in errors:
            print(f"  {old_name}: {error}")
    
    if dry_run:
        print(f"\n{'='*80}")
        print(f"This was a DRY RUN. No directories were actually renamed.")
        print(f"To perform the actual rename, run without --dry-run flag:")
        print(f"  python rename_workflows_with_paths.py {hold_dir}")
        print(f"{'='*80}")
    else:
        print(f"\n{'='*80}")
        print(f"Rename complete!")
        print(f"{'='*80}")


def main():
    parser = argparse.ArgumentParser(
        description='Rename workflow directories to include 2-component path identifiers',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (see what would be renamed without making changes)
  python rename_workflows_with_paths.py C:\\path\\to\\hold --dry-run
  
  # Actually perform the rename
  python rename_workflows_with_paths.py C:\\path\\to\\hold
  
  # Use default directory with dry run
  python rename_workflows_with_paths.py --dry-run

WARNING: This modifies directory names. Make sure you have backups before running!
"""
    )
    
    parser.add_argument(
        'hold_dir',
        nargs='?',
        default=r'C:\Users\kelly\GitHub\idt\idtexternal\idt\descriptions\hold',
        help='Path to directory containing workflow directories (default: C:\\Users\\kelly\\GitHub\\idt\\idtexternal\\idt\\descriptions\\hold)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be renamed without actually renaming (recommended for first run)'
    )
    
    args = parser.parse_args()
    
    rename_workflows(args.hold_dir, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
