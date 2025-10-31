#!/usr/bin/env python3
"""
Interactive Guided Workflow - Helps users build and run workflow commands
"""

import sys
import os
from pathlib import Path
import subprocess
import json
import argparse

# Add scripts directory to path
SCRIPT_DIR = Path(__file__).parent.absolute()
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# Import config loader
from config_loader import load_json_config


def print_header(text):
    """Print a section header"""
    print(f"\n{'=' * 70}")
    print(f"  {text}")
    print(f"{'=' * 70}\n")


def print_numbered_list(items, start=1):
    """Print a numbered list of items (accessible for screen readers)"""
    for idx, item in enumerate(items, start=start):
        print(f"  {idx}. {item}")
    print()


def get_choice(prompt, options, default=None, allow_back=False, allow_exit=True):
    """
    Get user choice from numbered list (accessible for screen readers)
    
    Args:
        prompt: Question to ask
        options: List of option strings
        default: Default option number (1-based) if user just presses Enter
        allow_back: If True, allow 'b' to go back
        allow_exit: If True, allow 'e' to exit
    
    Returns:
        Selected option string, or 'BACK' if user pressed 'b', or 'EXIT' if user pressed 'e'
    """
    print(prompt)
    print_numbered_list(options)
    
    # Build help text
    help_parts = []
    if allow_back:
        help_parts.append("b=back")
    if allow_exit:
        help_parts.append("e=exit")
    help_text = ", ".join(help_parts)
    
    while True:
        if default:
            if help_text:
                user_input = input(f"Enter choice (1-{len(options)}, {help_text}, default={default}): ").strip().lower()
            else:
                user_input = input(f"Enter choice (1-{len(options)}, default={default}): ").strip().lower()
            if not user_input:
                return options[default - 1]
        else:
            if help_text:
                user_input = input(f"Enter choice (1-{len(options)}, {help_text}): ").strip().lower()
            else:
                user_input = input(f"Enter choice (1-{len(options)}): ").strip().lower()
        
        # Check for special commands
        if user_input == 'b' and allow_back:
            return 'BACK'
        if user_input == 'e' and allow_exit:
            return 'EXIT'
        
        try:
            choice = int(user_input)
            if 1 <= choice <= len(options):
                return options[choice - 1]
            else:
                print(f"Please enter a number between 1 and {len(options)}")
        except ValueError:
            valid_options = f"a number between 1 and {len(options)}"
            if allow_back or allow_exit:
                extras = []
                if allow_back:
                    extras.append("'b' for back")
                if allow_exit:
                    extras.append("'e' for exit")
                valid_options += ", " + ", or ".join(extras)
            print(f"Please enter {valid_options}")


def get_input(prompt, default=None, allow_empty=False):
    """Get user input with optional default"""
    if default:
        result = input(f"{prompt} (default: {default}): ").strip()
        return result if result else default
    else:
        while True:
            result = input(f"{prompt}: ").strip()
            if result or allow_empty:
                return result
            print("This field is required. Please enter a value.")


def get_yes_no(prompt, default=True):
    """
    Get yes/no answer from user (accessible for screen readers)
    
    Args:
        prompt: Question to ask
        default: Default boolean value if user just presses Enter
    
    Returns:
        Boolean True for yes, False for no
    """
    default_str = "Y/n" if default else "y/N"
    while True:
        response = input(f"{prompt} [{default_str}]: ").strip().lower()
        if not response:
            return default
        if response in ['y', 'yes']:
            return True
        if response in ['n', 'no']:
            return False
        print("Please enter 'y' for yes or 'n' for no")


def create_view_results_bat(output_dir: Path):
    """
    Create a view_results.bat file in the root directory for easy viewer access.
    
    Args:
        output_dir: Path to the workflow output directory
    """
    try:
        # Get the base path (for both dev and executable scenarios)
        if getattr(sys, 'frozen', False):
            # Running as executable
            base_dir = Path(sys.executable).parent
            viewer_exe = base_dir / "viewer" / "viewer.exe"
        else:
            # Running from source
            base_dir = Path(__file__).parent.parent
            viewer_exe = base_dir / "viewer" / "viewer.py"
        
        # Create the batch file in the root directory
        bat_file = Path.cwd() / "view_results.bat"
        
        if viewer_exe.exists():
            with open(bat_file, 'w') as f:
                f.write("@echo off\n")
                f.write("REM Auto-generated by Image Description Toolkit\n")
                f.write("REM Double-click this file to view workflow results\n\n")
                
                if getattr(sys, 'frozen', False):
                    # Use executable path
                    f.write(f'start "" "{viewer_exe}" "{output_dir.absolute()}"\n')
                else:
                    # Use Python script
                    f.write(f'start "" "{sys.executable}" "{viewer_exe}" "{output_dir.absolute()}"\n')
    
    except Exception as e:
        # Silently fail - this is just a convenience feature
        pass


def check_api_key_file(provider):
    """Check if API key file exists"""
    key_files = {
        'openai': ['openai.txt', 'openai_key.txt'],
        'claude': ['claude.txt', 'claude_key.txt', 'anthropic.txt']
    }
    
    for filename in key_files.get(provider, []):
        if Path(filename).exists():
            return filename
    return None


def setup_api_key(provider):
    """Guide user through API key setup"""
    print(f"\n{provider.upper()} requires an API key.")
    
    existing_file = check_api_key_file(provider)
    if existing_file:
        print(f"Found existing API key file: {existing_file}")
        use_existing = get_choice("Use this key file?", ["Yes", "No, specify a different file"], allow_back=True)
        if use_existing == 'EXIT':
            return None
        if use_existing == 'BACK':
            return 'BACK'
        if use_existing == "Yes":
            # Convert to absolute path
            return str(Path(existing_file).resolve())
    
    print(f"\nYou can either:")
    print("  1. Specify the path to a file containing your API key")
    print("  2. Enter the API key now (will be saved to a file)")
    
    choice = get_choice("How would you like to provide the API key?", 
                       ["Path to existing key file", "Enter key now"], allow_back=True)
    
    if choice == 'EXIT':
        return None
    if choice == 'BACK':
        return 'BACK'
    
    if choice == "Path to existing key file":
        while True:
            key_path = get_input("Enter path to API key file")
            key_path_obj = Path(key_path)
            if key_path_obj.exists():
                # Convert to absolute path to avoid working directory issues
                return str(key_path_obj.resolve())
            else:
                print(f"File not found: {key_path}")
                retry = get_choice("Try again?", ["Yes", "No, skip API key setup"], allow_back=True)
                if retry == 'EXIT' or retry == "No, skip API key setup":
                    return None
                if retry == 'BACK':
                    return 'BACK'
    else:
        # Enter key and save it
        api_key = get_input(f"Enter your {provider.upper()} API key")
        if not api_key:
            return None
        
        filename = f"{provider}.txt"
        try:
            with open(filename, 'w') as f:
                f.write(api_key.strip())
            print(f"API key saved to: {filename}")
            # Return absolute path
            return str(Path(filename).resolve())
        except Exception as e:
            print(f"Error saving API key: {e}")
            return None


def check_ollama_models():
    """Get list of installed Ollama models (real-time check)"""
    try:
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            # Skip header line
            models = []
            for line in lines[1:]:
                if line.strip():
                    # Extract model name (first column)
                    model_name = line.split()[0]
                    models.append(model_name)
            return models
        return []
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []


def get_available_prompt_styles(custom_config_path=None):
    """
    Get available prompt styles from image_describer_config.json (real-time)
    
    Args:
        custom_config_path: Optional path to custom config file
    
    Returns:
        Tuple of (prompt_styles_list, default_style)
    """
    try:
        if custom_config_path:
            # Use custom config if provided
            print(f"  Loading prompts from custom config: {custom_config_path}")
            # Pass as explicit parameter, extract just filename for search
            config_filename = Path(custom_config_path).name
            config, path, source = load_json_config(config_filename, explicit=custom_config_path)
            if config:
                print(f"  ✓ Loaded config from: {path} (source: {source})")
                prompt_variations = config.get('prompt_variations', {})
                default_style = config.get('default_prompt_style', 'narrative')
                print(f"  ✓ Found {len(prompt_variations)} prompt styles")
                return list(prompt_variations.keys()), default_style
            else:
                print(f"  ✗ Failed to load custom config, falling back to default")
        
        # Fall back to default config loading
        config, path, source = load_json_config('image_describer_config.json')
        if config:
            prompt_variations = config.get('prompt_variations', {})
            default_style = config.get('default_prompt_style', 'narrative')
            return list(prompt_variations.keys()), default_style
        
        # Final fallback if config not found
        return ['narrative', 'detailed', 'concise', 'artistic', 'technical'], 'narrative'
    except Exception as e:
        print(f"  ✗ Error loading prompts: {e}")
        return ['narrative', 'detailed', 'concise', 'artistic', 'technical'], 'narrative'


def validate_directory(path):
    """Check if directory exists and contains images"""
    dir_path = Path(path)
    if not dir_path.exists():
        return False, "Directory does not exist"
    
    if not dir_path.is_dir():
        return False, "Path is not a directory"
    
    # Check for image files
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp', '.heic', '.heif'}
    has_images = any(f.suffix.lower() in image_extensions for f in dir_path.rglob('*'))
    
    if not has_images:
        return False, "No image files found in directory"
    
    return True, "Valid"


def guided_workflow(custom_config_path=None):
    """
    Interactive guided workflow builder
    
    Args:
        custom_config_path: Optional path to custom image_describer_config.json
    """
    # Parse any extra workflow arguments passed through (e.g., --timeout 300)
    # These will be appended to the final workflow command
    extra_workflow_args = []
    config_path_for_workflow = custom_config_path  # Store to pass to workflow
    
    if len(sys.argv) > 1:
        # Filter out any arguments that are meant for the workflow
        i = 1
        while i < len(sys.argv):
            arg = sys.argv[i]
            # Handle --config flag
            if arg in ['--config', '-c']:
                if i + 1 < len(sys.argv):
                    i += 1
                    config_path_for_workflow = sys.argv[i]
                    # Convert to absolute path for reliability
                    config_path_abs = Path(config_path_for_workflow).resolve()
                    if config_path_abs.exists():
                        config_path_for_workflow = str(config_path_abs)
                        print(f"\n✓ Using custom configuration: {config_path_for_workflow}")
                    else:
                        print(f"\n✗ Warning: Config file not found: {config_path_abs}")
                        print(f"   Will attempt to use default configuration instead.")
                        config_path_for_workflow = None
                i += 1
                continue
            # Known workflow flags to pass through
            if arg in ['--timeout', '--preserve-descriptions', '--metadata', '--no-metadata', '--no-geocode', '--geocode-cache']:
                extra_workflow_args.append(arg)
                # Check if next arg is the value for this flag
                if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith('--'):
                    i += 1
                    extra_workflow_args.append(sys.argv[i])
            i += 1
    
    print_header("Image Description Toolkit - Guided Workflow")
    
    print("Welcome! This wizard will help you set up and run an image description workflow.")
    print("You can press Ctrl+C at any time to exit.")
    
    # Show any extra workflow options that were provided
    if extra_workflow_args:
        print(f"\nAdditional workflow options: {' '.join(extra_workflow_args)}")
    print()
    
    # Step 1: Select Provider
    print_header("Step 1: Select AI Provider")
    providers = ["ollama", "openai", "claude"]
    provider = get_choice("Which AI provider would you like to use?", providers, default=1)
    
    if provider == 'EXIT':
        print("Exiting...")
        return
    
    # Step 2: API Key Setup (if needed for cloud providers)
    api_key_file = None
    if provider in ['openai', 'claude']:
        print_header(f"Step 2: {provider.upper()} API Key Setup")
        api_key_file = setup_api_key(provider)
        if api_key_file == 'BACK':
            # Go back to Step 1
            return guided_workflow()
        if not api_key_file:
            print(f"\nWarning: No API key configured. The workflow may fail without a valid API key.")
            cont = get_choice("Continue anyway?", ["Yes", "No, go back to setup"], allow_back=True)
            if cont == 'EXIT':
                print("Exiting...")
                return
            if cont == 'BACK' or cont == "No, go back to setup":
                return guided_workflow()
    
    # Step 2/3: Select Model (step number depends on whether API key was needed)
    model_step = "Step 2" if provider == 'ollama' else "Step 3"
    print_header(f"{model_step}: Select Model")
    
    if provider == 'ollama':
        print("Checking for installed Ollama models...")
        installed_models = check_ollama_models()
        
        if installed_models:
            print(f"Found {len(installed_models)} installed model(s)\n")
            model = get_choice("Select a model", installed_models, default=1, allow_back=True)
            if model == 'EXIT':
                print("Exiting...")
                return
            if model == 'BACK':
                # Go back to provider selection
                return guided_workflow()
        else:
            print("No Ollama models found or Ollama is not running.")
            print("Common vision models: llava, llava:7b, llava:13b, moondream, bakllava")
            model = get_input("Enter model name (e.g., 'llava:7b')", default="llava:7b")
    
    elif provider == 'openai':
        openai_models = [
            "gpt-4o (best quality, higher cost)",
            "gpt-4o-mini (good quality, lower cost)",
            "gpt-5 (experimental)"
        ]
        print("Available OpenAI models:")
        model_choice = get_choice("Select a model", openai_models, default=2, allow_back=True)
        if model_choice == 'EXIT':
            print("Exiting...")
            return
        if model_choice == 'BACK':
            # Go back to provider selection - restart function
            return guided_workflow()
        # Extract just the model name (before the space/parenthesis)
        model = model_choice.split()[0]
    
    elif provider == 'claude':
        claude_models = [
            "claude-sonnet-4-5-20250929 (best balance, recommended)",
            "claude-opus-4-1-20250805 (highest intelligence)",
            "claude-opus-4-20250514 (high intelligence, legacy)",
            "claude-sonnet-4-20250514 (fast, capable)",
            "claude-3-7-sonnet-20250219 (fast, capable, legacy)",
            "claude-3-5-haiku-20241022 (fastest, economical)",
            "claude-3-haiku-20240307 (economical, legacy)"
        ]
        print("Available Claude models:")
        model_choice = get_choice("Select a model", claude_models, default=1, allow_back=True)
        if model_choice == 'EXIT':
            print("Exiting...")
            return
        if model_choice == 'BACK':
            # Go back to provider selection - restart function
            return guided_workflow()
        # Extract just the model name (before the space/parenthesis)
        model = model_choice.split()[0]
    
    # Step 3/4: Image Directory (step number depends on whether API key was needed)
    dir_step = "Step 3" if provider == 'ollama' else "Step 4"
    print_header(f"{dir_step}: Image Directory")
    
    while True:
        img_dir = get_input("Enter path to directory containing images")
        valid, message = validate_directory(img_dir)
        if valid:
            print(f"✓ {message}")
            break
        else:
            print(f"✗ {message}")
            retry = get_choice("Try again?", ["Yes", "No, go back to model selection"], allow_back=True)
            if retry == 'EXIT':
                print("Exiting...")
                return
            if retry == 'BACK' or retry == "No, go back to model selection":
                return guided_workflow()
    
    # Step 4/5: Workflow Name (Optional)
    name_step = "Step 4" if provider == 'ollama' else "Step 5"
    print_header(f"{name_step}: Workflow Name (Optional)")
    print("You can provide a custom name for this workflow run.")
    print("If you skip this, a name will be auto-generated from the input directory.")
    workflow_name = get_input("Enter workflow name", allow_empty=True)
    
    # Step 5/6: Prompt Style (Optional)
    style_step = "Step 5" if provider == 'ollama' else "Step 6"
    print_header(f"{style_step}: Prompt Style (Optional)")
    
    # Get available prompt styles from config (using custom config if provided)
    available_styles, default_style = get_available_prompt_styles(config_path_for_workflow)
    
    print(f"Select a prompt style, or press Enter to use the default ({default_style}).")
    
    # Build options with descriptions
    style_options = []
    for style in available_styles:
        if style == default_style:
            style_options.append(f"{style} (default)")
        else:
            style_options.append(style)
    style_options.append("Skip (use default)")
    
    style_choice = get_choice("Select prompt style", style_options, allow_back=True)
    
    if style_choice == 'EXIT':
        print("Exiting...")
        return
    if style_choice == 'BACK':
        return guided_workflow()
    
    # Extract just the style name
    if style_choice.startswith("Skip"):
        prompt_style = None
    else:
        # Remove " (default)" suffix if present
        prompt_style = style_choice.replace(" (default)", "").strip()
    
    # Step for metadata configuration
    metadata_step = "Step 6" if provider == 'ollama' else "Step 7"
    print_header(f"{metadata_step}: Metadata Options")
    
    print("The workflow can extract metadata from your images (GPS coordinates, dates, camera info).")
    print("This metadata can be:")
    print("  • Added as a location/date prefix to descriptions (e.g., 'Austin, TX Mar 25, 2025: ...')")
    print("  • Included in the description text file")
    print("  • Used for workflow tracking and organization")
    print()
    
    metadata_choice = get_choice(
        "Enable metadata extraction?",
        ["Yes (recommended)", "No"],
        default=1,
        allow_back=True
    )
    
    if metadata_choice == "back":
        return None
    
    enable_metadata = (metadata_choice == "Yes (recommended)")
    
    enable_geocoding = False
    geocode_cache_file = None
    
    if enable_metadata:
        print()
        print("Geocoding converts GPS coordinates into human-readable locations (city, state, country).")
        print("This requires internet access and adds a small delay per unique location.")
        print("Results are cached to minimize API calls on subsequent runs.")
        print()
        
        geocoding_choice = get_choice(
            "Enable geocoding to convert GPS to city/state/country?",
            ["Yes", "No (skip geocoding)"],
            default=2,
            allow_back=True
        )
        
        if geocoding_choice == "back":
            return None
        
        enable_geocoding = (geocoding_choice == "Yes")
        
        if enable_geocoding:
            print()
            print("Geocoding results are cached to avoid redundant API calls.")
            geocode_cache_file = get_input("Geocoding cache file location", default="geocode_cache.json")
    
    # Add metadata flags to extra_workflow_args
    if not enable_metadata:
        extra_workflow_args.append("--no-metadata")
    
    # Geocoding is now enabled by default in workflow.py, so we only need to pass --no-geocode if disabled
    if enable_metadata and not enable_geocoding:
        extra_workflow_args.append("--no-geocode")
    
    # Only add custom geocode cache location if specified and different from default
    if enable_geocoding and geocode_cache_file and geocode_cache_file.strip() and geocode_cache_file != "geocode_cache.json":
        extra_workflow_args.extend(["--geocode-cache", geocode_cache_file])
    
    # Build the command
    print_header("Command Summary")
    
    cmd_parts = ["idt", "workflow", img_dir]
    cmd_parts.extend(["--provider", provider])
    cmd_parts.extend(["--model", model])
    cmd_parts.extend(["--output-dir", "Descriptions"])  # Default output directory
    
    if api_key_file:
        cmd_parts.extend(["--api-key-file", api_key_file])
    
    if workflow_name:
        cmd_parts.extend(["--name", workflow_name])
    
    if prompt_style:
        cmd_parts.extend(["--prompt-style", prompt_style])
    
    # Add custom config if provided
    if config_path_for_workflow:
        cmd_parts.extend(["--config", config_path_for_workflow])
    
    # Add any extra workflow arguments passed to guideme
    if extra_workflow_args:
        cmd_parts.extend(extra_workflow_args)
    
    # Display the command
    command_str = " ".join(f'"{part}"' if ' ' in part else part for part in cmd_parts)
    print("The following command will be executed:\n")
    print(f"  {command_str}\n")
    
    # Ask to run or exit
    action = get_choice("What would you like to do?", 
                       ["Run this command now", "Just show the command (don't run)", "Go back to modify settings"],
                       allow_exit=True)
    
    if action == 'EXIT':
        print("Exiting...")
        return
    
    if action == "Go back to modify settings":
        return guided_workflow()
    
    # If running now, ask about output directory
    output_dir = "Descriptions"  # Default
    if action == "Run this command now":
        print_header("Output Directory")
        print("Where should the workflow results be saved?")
        print(f"Default: {output_dir}")
        print()
        
        custom_output = get_choice("Output directory:", 
                                  [f"Use default ({output_dir})", "Specify custom directory"],
                                  allow_exit=True, allow_back=True)
        
        if custom_output == 'EXIT':
            print("Exiting...")
            return
        
        if custom_output == 'BACK':
            return guided_workflow()
        
        if custom_output == "Specify custom directory":
            output_dir = input("\nEnter output directory path: ").strip()
            if not output_dir:
                print("No directory specified, using default: Descriptions")
                output_dir = "Descriptions"
            else:
                print(f"Using output directory: {output_dir}")
        
        # Rebuild command with final output directory
        cmd_parts = ["idt", "workflow", img_dir]
        cmd_parts.extend(["--provider", provider])
        cmd_parts.extend(["--model", model])
        cmd_parts.extend(["--output-dir", output_dir])
        
        if api_key_file:
            cmd_parts.extend(["--api-key-file", api_key_file])
        
        if workflow_name:
            cmd_parts.extend(["--name", workflow_name])
        
        if prompt_style:
            cmd_parts.extend(["--prompt-style", prompt_style])
        
        # Add custom config if provided
        if config_path_for_workflow:
            cmd_parts.extend(["--config", config_path_for_workflow])
        
        # Add any extra workflow arguments
        if extra_workflow_args:
            cmd_parts.extend(extra_workflow_args)
        
        command_str = " ".join(f'"{part}"' if ' ' in part else part for part in cmd_parts)
        
        print_header("Running Workflow")
        print(f"Executing: {command_str}\n")
        
        # Create view_results.bat file for easy viewer access
        output_path = Path(output_dir)
        create_view_results_bat(output_path)
        
        print("INFO: To view results in real-time, run: view_results.bat")
        print("      (Wait a few seconds after workflow starts for directory to be created)\n")
        
        # Run the actual workflow
        try:
            # Import and call the workflow directly
            from workflow import main as workflow_main
            
            # Build arguments for workflow
            workflow_args = [img_dir, "--provider", provider, "--model", model, "--output-dir", output_dir]
            if api_key_file:
                workflow_args.extend(["--api-key-file", api_key_file])
            if workflow_name:
                workflow_args.extend(["--name", workflow_name])
            if prompt_style:
                workflow_args.extend(["--prompt-style", prompt_style])
            # Add custom config if provided
            if config_path_for_workflow:
                workflow_args.extend(["--config", config_path_for_workflow])
            # Add any extra workflow arguments (e.g., --timeout)
            if extra_workflow_args:
                workflow_args.extend(extra_workflow_args)
            
            # Save original argv and replace with our args
            original_argv = sys.argv
            sys.argv = ['workflow.py'] + workflow_args
            
            try:
                workflow_main()
            finally:
                sys.argv = original_argv
                
        except Exception as e:
            print(f"\nError running workflow: {e}")
            print("\nYou can manually run the command shown above.")
    
    elif action == "Just show the command (don't run)":
        print("\nCopy and paste this command to run it:\n")
        print(f"  {command_str}\n")
        
        # Ask if they want to go back or exit
        next_action = get_choice("What next?", ["Go back to modify settings", "Exit"], allow_exit=True)
        if next_action == "Go back to modify settings":
            return guided_workflow()
        print("Exiting...")
        return


def main():
    """Main entry point"""
    try:
        guided_workflow()
    except KeyboardInterrupt:
        print("\n\nCancelled by user. Exiting...")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
