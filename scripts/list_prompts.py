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


def load_prompt_styles(config_file=None):
    """
    Load prompt styles from the configuration file.
    
    Args:
        config_file: Optional path to custom config file
    
    Returns:
        tuple: (default_style, prompt_variations dict, config_path)
    """
    # Use config_loader for proper resolution
    script_dir = Path(__file__).parent
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))
    
    try:
        from config_loader import load_json_config
        
        # Use custom config if provided, otherwise use default
        # Pass as explicit parameter if custom path provided
        if config_file:
            config, config_path, source = load_json_config('image_describer_config.json', explicit=config_file)
        else:
            config, config_path, source = load_json_config('image_describer_config.json')
        
        if not config:
            print("Error: Could not find image_describer_config.json", file=sys.stderr)
            print("\nSearched using config_loader resolution order", file=sys.stderr)
            return None, None, None
        
        default_style = config.get("default_prompt_style", "narrative")
        prompt_variations = config.get("prompt_variations", {})
        
        return default_style, prompt_variations, config_path
        
    except ImportError:
        # Fallback if config_loader not available (shouldn't happen)
        print("Error: config_loader module not found", file=sys.stderr)
        return None, None, None
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse JSON config file: {e}", file=sys.stderr)
        return None, None, None
    except Exception as e:
        print(f"Error: Failed to load config file: {e}", file=sys.stderr)
        return None, None, None


def list_prompts_simple(config_file=None):
    """List prompt style names only (simple format)."""
    default_style, prompt_variations, config_path = load_prompt_styles(config_file)
    
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


def list_prompts_verbose(config_file=None):
    """List prompt style names and their full text (verbose format)."""
    default_style, prompt_variations, config_path = load_prompt_styles(config_file)
    
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

  # Use custom config file
  idt prompt-list --config scripts/my_prompts.json
  idt prompt-list --config scripts/my_prompts.json --verbose

  # Also works with short form
  idt prompt-list -c scripts/my_prompts.json -v
        """
    )
    
    parser.add_argument(
        "--config", "-c",
        type=str,
        help="Path to custom image_describer_config.json file (contains prompt variations)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show full prompt text for each style (not just names)"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        return list_prompts_verbose(args.config)
    else:
        return list_prompts_simple(args.config)


if __name__ == "__main__":
    sys.exit(main())
