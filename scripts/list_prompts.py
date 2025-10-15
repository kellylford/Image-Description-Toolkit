#!/usr/bin/env python3
"""
List available prompt styles from configuration.

This utility reads the image_describer_config.json file and displays
all available prompt styles, optionally with their full text.
"""

import sys
import json
from pathlib import Path
import argparse


def find_config_file():
    """
    Find the image_describer_config.json file.
    Checks multiple possible locations.
    
    Returns:
        Path to config file or None if not found
    """
    # Possible config file locations
    possible_paths = [
        Path("image_describer_config.json"),  # Current directory
        Path("scripts/image_describer_config.json"),  # scripts subdirectory
        Path(__file__).parent / "image_describer_config.json",  # Same dir as this script
        Path(__file__).parent.parent / "scripts" / "image_describer_config.json",  # Up one level
    ]
    
    for config_path in possible_paths:
        if config_path.exists():
            return config_path
    
    return None


def load_prompt_styles():
    """
    Load prompt styles from the configuration file.
    
    Returns:
        tuple: (default_style, prompt_variations dict, config_path)
    """
    config_path = find_config_file()
    
    if not config_path:
        print("Error: Could not find image_describer_config.json", file=sys.stderr)
        print("\nSearched in:", file=sys.stderr)
        print("  - Current directory", file=sys.stderr)
        print("  - scripts/ subdirectory", file=sys.stderr)
        print("  - Script's parent directory", file=sys.stderr)
        return None, None, None
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        default_style = config.get("default_prompt_style", "narrative")
        prompt_variations = config.get("prompt_variations", {})
        
        return default_style, prompt_variations, config_path
        
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse JSON config file: {e}", file=sys.stderr)
        return None, None, None
    except Exception as e:
        print(f"Error: Failed to load config file: {e}", file=sys.stderr)
        return None, None, None


def list_prompts_simple():
    """List prompt style names only (simple format)."""
    default_style, prompt_variations, config_path = load_prompt_styles()
    
    if prompt_variations is None:
        return 1
    
    if not prompt_variations:
        print("No prompt styles found in configuration.")
        return 1
    
    print("Available Prompt Styles:")
    print("=" * 50)
    
    # Get sorted list of styles
    styles = sorted(prompt_variations.keys())
    
    # Print each style, marking the default
    for style in styles:
        if style == default_style:
            print(f"  {style} (default)")
        else:
            print(f"  {style}")
    
    print()
    print(f"Total: {len(styles)} prompt styles available")
    print(f"Config file: {config_path}")
    print()
    print("Use --verbose to see full prompt text for each style.")
    
    return 0


def list_prompts_verbose():
    """List prompt style names and their full text (verbose format)."""
    default_style, prompt_variations, config_path = load_prompt_styles()
    
    if prompt_variations is None:
        return 1
    
    if not prompt_variations:
        print("No prompt styles found in configuration.")
        return 1
    
    print("Available Prompt Styles (with full text):")
    print("=" * 70)
    print()
    
    # Get sorted list of styles
    styles = sorted(prompt_variations.keys())
    
    # Print each style with its full text
    for i, style in enumerate(styles, 1):
        prompt_text = prompt_variations[style]
        
        # Header with style name
        if style == default_style:
            print(f"{i}. {style} (DEFAULT)")
        else:
            print(f"{i}. {style}")
        
        print("-" * 70)
        
        # Print the prompt text with indentation
        # Handle multi-line prompts properly
        lines = prompt_text.split('\n')
        for line in lines:
            print(f"   {line}")
        
        print()  # Blank line between styles
    
    print("=" * 70)
    print(f"Total: {len(styles)} prompt styles available")
    print(f"Default style: {default_style}")
    print(f"Config file: {config_path}")
    
    return 0


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(
        description="List available prompt styles for image description",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List prompt style names only
  python list_prompts.py
  idt prompt-list

  # List with full prompt text
  python list_prompts.py --verbose
  idt prompt-list --verbose

  # Also works with
  idt prompt-list -v
        """
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show full prompt text for each style (not just names)"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        return list_prompts_verbose()
    else:
        return list_prompts_simple()


if __name__ == "__main__":
    sys.exit(main())
