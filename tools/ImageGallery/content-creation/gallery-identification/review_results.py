#!/usr/bin/env python3
"""
Gallery Results Reviewer - Quick review of gallery identification results
"""

import json
import sys
from pathlib import Path

def review_results(results_file):
    """Review gallery identification results"""
    
    print("=" * 70)
    print("  GALLERY RESULTS REVIEWER")
    print("=" * 70)
    
    # Load results
    try:
        with open(results_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"ERROR: Could not load results file: {e}")
        return
    
    candidates = data.get('candidates', [])
    config = data.get('configuration', {})
    
    print(f"\nGallery: {config.get('gallery_name', 'Unknown')}")
    print(f"Found: {len(candidates)} candidates")
    print(f"Search criteria: {config.get('content_rules', {})}")
    print()
    
    # Show all candidates with details
    for i, candidate in enumerate(candidates, 1):
        print(f"{i:2d}. {candidate.get('filename', 'Unknown file')}")
        print(f"    Score: {candidate.get('score', 0)}")
        print(f"    Path: {candidate.get('file_path', 'Unknown path')}")
        
        # Show keyword matches
        matches = candidate.get('keyword_matches', {})
        if matches.get('required'):
            print(f"    Required keywords: {', '.join(matches['required'])}")
        if matches.get('preferred'):
            print(f"    Preferred keywords: {', '.join(matches['preferred'])}")
        
        # Show a snippet of the description
        description = candidate.get('description', '')
        if description:
            snippet = description[:100] + "..." if len(description) > 100 else description
            print(f"    Description: {snippet}")
        
        print()
        
        # Pause every 10 items for easier reading
        if i % 10 == 0 and i < len(candidates):
            input(f"--- Showing {i} of {len(candidates)} - Press Enter to continue ---")
    
    print("=" * 70)
    print("REVIEW COMPLETE")
    print("=" * 70)
    print("\nNext steps:")
    print("1. Copy your favorite image files to a gallery directory")
    print("2. Use the existing ImageGallery tools to build your gallery")
    print("3. The file paths above show you exactly where each image is located")

def main():
    if len(sys.argv) != 2:
        print("Usage: python review_results.py <results_file.json>")
        print()
        print("Examples:")
        print("  python review_results.py orange_final_results.json")
        print("  python review_results.py findthesun_results.json")
        return 1
    
    results_file = sys.argv[1]
    if not Path(results_file).exists():
        print(f"ERROR: Results file not found: {results_file}")
        return 1
    
    review_results(results_file)
    return 0

if __name__ == "__main__":
    sys.exit(main())