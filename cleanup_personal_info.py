#!/usr/bin/env python3
"""
Personal Information Cleanup Script for Image Description Toolkit

This script removes personal paths and information from documentation and config files
while preserving functionality and proper attribution.

SAFE TO RUN:
- All replacements are carefully designed to not break functionality
- Creates backups before modification
- Provides a dry-run mode to preview changes
- Skips binary files and git directories

Author: Image Description Toolkit Team
License: MIT
"""

import os
import re
import shutil
from pathlib import Path
from typing import List, Tuple, Dict
import argparse
import json

# Define safe replacement patterns
REPLACEMENTS = [
    # Config file specific - replace absolute path with relative default
    {
        "pattern": r'"output_directory":\s*"C:\\\\Users\\\\kelly\\\\GitHub\\\\Image-Description-Toolkit\\\\Descriptions\\\\[^"]*"',
        "replacement": '"output_directory": "extracted_frames"',
        "files": ["scripts/video_frame_extractor_config.json"],
        "description": "Replace hardcoded output directory with relative path default"
    },
    
    # OneDrive API key path examples - replace with generic examples
    {
        "pattern": r'c:/users/kelly/onedrive/idt/claude\.txt',
        "replacement": r'~/.config/idt/claude.txt',
        "files": ["tools/**/*.md"],
        "description": "Replace OneDrive Claude API key path with generic XDG path"
    },
    {
        "pattern": r'/c/users/kelly/onedrive/idt/claude\.txt',
        "replacement": r'~/.config/idt/claude.txt',
        "files": ["tools/**/*.md"],
        "description": "Replace OneDrive Claude API key path (Unix style) with generic XDG path"
    },
    {
        "pattern": r'c:\\users\\kelly\\onedrive\\',
        "replacement": r'~/your_secure_location/',
        "files": ["docs/**/*.md"],
        "description": "Replace OneDrive references in docs with generic path"
    },
    
    # Development machine paths in documentation - replace with examples
    {
        "pattern": r'C:\\Users\\kelly\\GitHub\\Image-Description-Toolkit',
        "replacement": r'C:\\Path\\To\\Image-Description-Toolkit',
        "files": ["docs/**/*.md", "tools/**/*.md", "*.md"],
        "description": "Replace Windows dev path with generic example"
    },
    {
        "pattern": r'/c/Users/kelly/GitHub/Image-Description-Toolkit',
        "replacement": r'/path/to/Image-Description-Toolkit',
        "files": ["docs/**/*.md", "tools/**/*.md", "*.md"],
        "description": "Replace Unix-style dev path with generic example"
    },
    {
        "pattern": r'C:/Users/kelly/GitHub/Image-Description-Toolkit',
        "replacement": r'C:/Path/To/Image-Description-Toolkit',
        "files": ["docs/**/*.md", "tools/**/*.md", "*.md"],
        "description": "Replace mixed-style Windows path with generic example"
    },
    
    # git-ignored personal batch files - these are safe to mention but clarify
    {
        "pattern": r'tools/kelly_release_and_install\.bat',
        "replacement": r'tools/your_personal_workflow.bat (git-ignored)',
        "files": ["tools/**/*.md"],
        "description": "Clarify personal workflow scripts are git-ignored examples"
    },
]

# Files to always skip
SKIP_PATTERNS = [
    r'\.git/',
    r'\.venv/',
    r'\.winenv/',
    r'\.macenv/',
    r'__pycache__/',
    r'\.pyc$',
    r'\.exe$',
    r'\.dll$',
    r'\.pyd$',
    r'\.so$',
    r'build/',
    r'dist/',
    r'\.egg-info/',
    r'node_modules/',
    # Keep these files as-is (historical logs, internal notes)
    r'docs/WorkTracking/comparison_results.*\.json',
    r'docs/WorkTracking/.*session.*\.md',  # Session summaries are historical
    r'viewer/INTEGRATION_COMPLETE\.txt',  # Internal development notes
    r'LICENSE',  # Keep copyright as-is
]

# Files to DEFINITELY process (high priority user-facing docs)
PRIORITY_FILES = [
    "README.md",
    "docs/USER_GUIDE_V4.md",
    "docs/USER_GUIDE.md",
    "docs/CONFIGURATION_GUIDE.md",
    "docs/CLI_REFERENCE.md",
    "scripts/video_frame_extractor_config.json",
    "tools/ImageGallery/documentation/REPLICATION_GUIDE.md",
    "tools/ImageGallery/documentation/SETUP_GUIDE.md",
]


def should_skip_file(file_path: Path) -> bool:
    """Check if file should be skipped based on patterns"""
    path_str = str(file_path).replace('\\', '/')
    for pattern in SKIP_PATTERNS:
        if re.search(pattern, path_str):
            return True
    return False


def is_text_file(file_path: Path) -> bool:
    """Check if file is likely a text file"""
    text_extensions = {
        '.md', '.txt', '.json', '.py', '.bat', '.sh', '.command',
        '.html', '.css', '.js', '.yaml', '.yml', '.toml', '.ini',
        '.cfg', '.conf', '.xml', '.rst', '.log'
    }
    return file_path.suffix.lower() in text_extensions


def match_glob_pattern(file_path: Path, pattern: str, repo_root: Path) -> bool:
    """Check if file matches a glob pattern"""
    # Convert to relative path from repo root
    try:
        rel_path = file_path.relative_to(repo_root)
    except ValueError:
        return False
    
    # Simple glob matching
    if '**' in pattern:
        # Recursive glob
        parts = pattern.split('/')
        if parts[0] == '**':
            # Match anywhere
            return any(part in str(rel_path) for part in parts[1:])
        else:
            # Match from specific directory
            return str(rel_path).startswith(parts[0])
    else:
        # Direct match
        return str(rel_path) == pattern


def find_files_for_replacement(replacement: Dict, repo_root: Path) -> List[Path]:
    """Find all files matching the replacement pattern"""
    files_to_process = []
    
    for file_pattern in replacement["files"]:
        if '**' in file_pattern or '*' in file_pattern:
            # Glob pattern - walk directory
            for root, dirs, files in os.walk(repo_root):
                # Skip directories in SKIP_PATTERNS
                dirs[:] = [d for d in dirs if not should_skip_file(Path(root) / d)]
                
                for file in files:
                    file_path = Path(root) / file
                    if should_skip_file(file_path):
                        continue
                    if not is_text_file(file_path):
                        continue
                    if match_glob_pattern(file_path, file_pattern, repo_root):
                        files_to_process.append(file_path)
        else:
            # Direct file path
            file_path = repo_root / file_pattern
            if file_path.exists() and is_text_file(file_path):
                files_to_process.append(file_path)
    
    return list(set(files_to_process))  # Remove duplicates


def preview_changes(file_path: Path, pattern: str, replacement: str) -> Tuple[int, List[str]]:
    """Preview what changes would be made to a file"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        matches = list(re.finditer(pattern, content, re.IGNORECASE))
        match_count = len(matches)
        
        preview_lines = []
        for i, match in enumerate(matches[:3], 1):  # Show first 3 matches
            start = max(0, match.start() - 30)
            end = min(len(content), match.end() + 30)
            context = content[start:end]
            preview_lines.append(f"  Match {i}: ...{context}...")
        
        if len(matches) > 3:
            preview_lines.append(f"  ... and {len(matches) - 3} more matches")
        
        return match_count, preview_lines
    except Exception as e:
        return 0, [f"  Error reading file: {e}"]


def apply_replacement(file_path: Path, pattern: str, replacement: str, dry_run: bool = False) -> Tuple[bool, int]:
    """Apply replacement to a file, return (success, num_replacements)"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            original_content = f.read()
        
        new_content, num_replacements = re.subn(pattern, replacement, original_content, flags=re.IGNORECASE)
        
        if num_replacements > 0 and not dry_run:
            # Create backup
            backup_path = file_path.with_suffix(file_path.suffix + '.backup')
            shutil.copy2(file_path, backup_path)
            
            # Write new content
            with open(file_path, 'w', encoding='utf-8', newline='') as f:
                f.write(new_content)
        
        return True, num_replacements
    except Exception as e:
        print(f"    [ERROR] {e}")
        return False, 0


def main():
    parser = argparse.ArgumentParser(
        description="Clean personal information from Image Description Toolkit repository",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview changes without modifying files
  python cleanup_personal_info.py --dry-run
  
  # Apply changes with verbose output
  python cleanup_personal_info.py --verbose
  
  # Clean only specific categories
  python cleanup_personal_info.py --category config --category docs
        """
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without modifying files'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed output'
    )
    parser.add_argument(
        '--category',
        action='append',
        choices=['config', 'docs', 'all'],
        help='Limit to specific categories (can specify multiple times)'
    )
    
    args = parser.parse_args()
    
    # Find repository root
    repo_root = Path(__file__).parent
    print(f"[INFO] Repository root: {repo_root}\n")
    
    if args.dry_run:
        print("[DRY RUN] No files will be modified\n")
    
    total_files_modified = 0
    total_replacements = 0
    
    for replacement in REPLACEMENTS:
        print(f"[TASK] {replacement['description']}")
        
        # Find matching files
        matching_files = find_files_for_replacement(replacement, repo_root)
        
        if not matching_files:
            print("   [INFO] No matching files found\n")
            continue
        
        print(f"   Found {len(matching_files)} file(s)")
        
        for file_path in matching_files:
            rel_path = file_path.relative_to(repo_root)
            
            if args.dry_run or args.verbose:
                count, preview = preview_changes(
                    file_path,
                    replacement['pattern'],
                    replacement['replacement']
                )
                
                if count > 0:
                    print(f"   [FILE] {rel_path}: ({count} match{'es' if count != 1 else ''})")
                    if args.verbose:
                        for line in preview:
                            print(line)
            
            if not args.dry_run:
                success, num_replacements = apply_replacement(
                    file_path,
                    replacement['pattern'],
                    replacement['replacement'],
                    dry_run=False
                )
                
                if num_replacements > 0:
                    total_files_modified += 1
                    total_replacements += num_replacements
                    print(f"   [OK] {rel_path}: {num_replacements} replacement(s)")
        
        print()
    
    # Summary
    print("=" * 60)
    if args.dry_run:
        print("[DRY RUN] COMPLETE - No files were modified")
        print("Run without --dry-run to apply changes")
    else:
        print("[SUCCESS] CLEANUP COMPLETE")
        print(f"   Files modified: {total_files_modified}")
        print(f"   Total replacements: {total_replacements}")
        print(f"   Backups created: {total_files_modified} (.backup files)")
        print("\n[TIP] To restore from backup: move file.backup file")
        print("[TIP] To remove backups: del /s *.backup (Windows) or find . -name '*.backup' -delete (Unix)")


if __name__ == '__main__':
    main()
