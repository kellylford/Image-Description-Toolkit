#!/usr/bin/env python3
"""
Gallery Content Identification Wizard - Interactive tool for creating themed galleries
"""

import sys
import os
import json
from pathlib import Path
import subprocess
from datetime import datetime, timedelta

# Add parent directory to path for imports
SCRIPT_DIR = Path(__file__).parent.absolute()
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def create_idw_workspace(results_file, workflows_dir):
    """Create IDW workspace file from gallery results"""
    try:
        # Import the IDW creator
        from create_gallery_idw import GalleryIDWCreator
        
        # Create the workspace
        creator = GalleryIDWCreator()
        
        # Generate output filename
        results_path = Path(results_file)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        idw_file = results_path.parent / f"gallery_workspace_{timestamp}.idw"
        
        # Create workspace
        created_file = creator.create_gallery_idw(
            results_file=results_path,
            workflows_dir=Path(workflows_dir),
            output_file=idw_file,
            workspace_name=f"Gallery_{timestamp}"
        )
        
        return created_file
        
    except ImportError:
        print("❌ Error: create_gallery_idw.py not found")
        return None
    except Exception as e:
        print(f"❌ Error creating IDW workspace: {e}")
        return None


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


def get_keywords_input(prompt, examples=None):
    """Get comma-separated keywords from user"""
    if examples:
        print(f"\nExamples: {', '.join(examples[:5])}")
    
    while True:
        result = input(f"{prompt}: ").strip()
        if result:
            # Split by comma and clean up
            keywords = [kw.strip() for kw in result.split(',') if kw.strip()]
            if keywords:
                return keywords
        print("Please enter at least one keyword (separate multiple keywords with commas)")


def check_directory_exists(path_str):
    """Check if a directory exists and is accessible"""
    try:
        path = Path(path_str)
        if path.exists() and path.is_dir():
            # Try to list contents to check accessibility
            list(path.iterdir())
            return True
    except (OSError, PermissionError):
        pass
    return False


def welcome_screen():
    """Show welcome screen and get started"""
    print_header("🌟 Gallery Content Identification Wizard")
    
    print("Welcome to the Gallery Content Identification Wizard!")
    print()
    print("This tool helps you automatically find and select images for themed galleries")
    print("from your IDT workflow results using keyword matching and smart filtering.")
    print()
    print("✨ What this wizard does:")
    print("  • Guides you through setting up gallery search criteria")
    print("  • Scans your described images for matches")
    print("  • Creates ranked lists of the best candidates")
    print("  • Saves configurations for reuse")
    print()
    print("📁 You'll need:")
    print("  • IDT workflow results (described images)")
    print("  • An idea of what theme you want (keywords)")
    print()
    
    choice = get_choice("Ready to get started?", 
                       ["🚀 Start the wizard", "📖 Use an example configuration", "❌ Exit"])
    
    if choice == "❌ Exit":
        print("\nThanks for trying the Gallery Content Identification Wizard!")
        return 'EXIT'
    elif choice == "📖 Use an example configuration":
        return 'EXAMPLES'
    else:
        return 'WIZARD'


def show_examples():
    """Show example configurations and let user run one"""
    print_header("📖 Example Gallery Configurations")
    
    examples = [
        ("🌅 Sunshine On The Water", "sunset_water.json", "Water scenes with beautiful sunlight"),
        ("🏔️ Mountain Adventures", "mountains.json", "Mountain landscapes and hiking scenes"),
        ("🏢 Urban Architecture", "architecture.json", "Buildings and city structures"),
        ("🦌 Wildlife & Nature", "wildlife.json", "Animals and natural scenes"),
        ("🍽️ Food Photography", "food.json", "Delicious dishes and cuisine"),
        ("🔧 Create custom configuration", "CUSTOM", "Build your own from scratch")
    ]
    
    print("Choose an example to run, or create your own:")
    print()
    
    options = [f"{name} - {desc}" for name, _, desc in examples]
    choice = get_choice("Which would you like to use?", options, allow_back=True)
    
    if choice == 'BACK':
        return 'BACK'
    
    # Find selected example
    selected_idx = options.index(choice)
    name, config_file, desc = examples[selected_idx]
    
    if config_file == "CUSTOM":
        return 'WIZARD'
    
    # Check if example config exists
    config_path = SCRIPT_DIR / "example_configs" / config_file
    if not config_path.exists():
        print(f"\n❌ Example configuration file not found: {config_file}")
        print("Please use the custom wizard instead.")
        input("\nPress Enter to continue...")
        return 'WIZARD'
    
    print(f"\n✅ Selected: {name}")
    print(f"Description: {desc}")
    print(f"Configuration: {config_file}")
    
    # Ask for scan directory
    print(f"\n📁 Where should we scan for your described images?")
    scan_dirs = get_scan_directories()
    if scan_dirs == 'BACK':
        return 'BACK'
    
    # Run with the example config
    return run_identification(config_path, scan_dirs, name)


def get_scan_directories():
    """Get directories to scan for described images"""
    print_header("📁 Choose Scan Directories")
    
    print("Where are your IDT workflow results stored?")
    print("(These are directories containing described images)")
    print()
    
    common_locations = [
        ("./descriptions", "Current directory descriptions folder"),
        ("//qnap/home/idt/descriptions", "QNAP server descriptions"),
        ("C:\\idt\\descriptions", "Standard Windows IDT location"),
        ("Enter custom path", "Specify a different location")
    ]
    
    options = [f"{path} - {desc}" for path, desc in common_locations]
    choice = get_choice("Select your descriptions directory:", options, allow_back=True)
    
    if choice == 'BACK':
        return 'BACK'
    
    selected_idx = options.index(choice)
    if selected_idx == len(common_locations) - 1:  # Custom path
        while True:
            custom_path = get_input("Enter the full path to your descriptions directory")
            if check_directory_exists(custom_path):
                return [custom_path]
            else:
                print(f"❌ Directory not found or not accessible: {custom_path}")
                retry = get_choice("What would you like to do?", 
                                 ["Try another path", "Continue anyway (might fail later)"], 
                                 allow_back=True)
                if retry == 'BACK':
                    return 'BACK'
                elif retry == "Continue anyway (might fail later)":
                    return [custom_path]
    else:
        path = common_locations[selected_idx][0]
        if not check_directory_exists(path):
            print(f"\n⚠️ Warning: Directory not found or not accessible: {path}")
            continue_anyway = get_choice("What would you like to do?", 
                                       ["Continue anyway (might work during scan)", 
                                        "Choose different directory"], 
                                       allow_back=True)
            if continue_anyway == 'BACK':
                return 'BACK'
            elif continue_anyway == "Choose different directory":
                return get_scan_directories()
        
        return [path]


def wizard_mode():
    """Main wizard flow for creating custom configuration"""
    print_header("🧙 Custom Gallery Configuration Wizard")
    
    config = {
        "gallery_name": "",
        "sources": {
            "directories": [],
            "workflow_patterns": ["*"]
        },
        "content_rules": {
            "required_keywords": [],
            "preferred_keywords": [],
            "excluded_keywords": [],
            "min_keyword_matches": 1,
            "case_sensitive": False
        },
        "filters": {
            "min_description_length": 0,
            "preferred_prompts": [],
            "preferred_models": []
        },
        "output": {
            "max_images": 50,
            "sort_by": "keyword_relevance",
            "include_metadata": True
        }
    }
    
    # Step 1: Gallery name
    print("🎯 Step 1: Gallery Theme")
    print("What's the theme or name for your gallery?")
    print("Examples: 'Sunset Memories', 'Urban Adventures', 'Family Vacation 2025'")
    config["gallery_name"] = get_input("Gallery name")
    
    # Step 2: Scan directories
    print(f"\n📁 Step 2: Scan Locations")
    scan_dirs = get_scan_directories()
    if scan_dirs == 'BACK':
        return 'BACK'
    config["sources"]["directories"] = scan_dirs
    
    # Step 3: Required keywords
    print(f"\n🔍 Step 3: Required Keywords")
    print("What keywords MUST be present in image descriptions?")
    print("Images without ALL of these keywords will be excluded.")
    
    has_required = get_choice("Do you want to require specific keywords?", 
                            ["Yes, I have must-have keywords", "No, any images are fine"])
    
    if has_required == "Yes, I have must-have keywords":
        config["content_rules"]["required_keywords"] = get_keywords_input(
            "Enter required keywords (comma-separated)",
            ["water", "mountain", "building", "food", "animal"]
        )
    
    # Step 4: Preferred keywords
    print(f"\n⭐ Step 4: Preferred Keywords")
    print("What keywords would you LIKE to see (bonus points)?")
    print("Images with these keywords will be ranked higher.")
    
    has_preferred = get_choice("Do you want to specify preferred keywords?", 
                             ["Yes, add preferred keywords", "No, skip this"])
    
    if has_preferred == "Yes, add preferred keywords":
        config["content_rules"]["preferred_keywords"] = get_keywords_input(
            "Enter preferred keywords (comma-separated)",
            ["sunset", "beautiful", "scenic", "colorful", "artistic"]
        )
    
    # Step 5: Excluded keywords
    print(f"\n🚫 Step 5: Excluded Keywords")
    print("What keywords should EXCLUDE images from your gallery?")
    print("Images with these keywords will be filtered out completely.")
    
    has_excluded = get_choice("Do you want to exclude certain keywords?", 
                            ["Yes, exclude unwanted content", "No, include everything"])
    
    if has_excluded == "Yes, exclude unwanted content":
        config["content_rules"]["excluded_keywords"] = get_keywords_input(
            "Enter excluded keywords (comma-separated)",
            ["dark", "blurry", "indoor", "night", "poor quality"]
        )
    
    # Step 6: Advanced options
    print(f"\n⚙️ Step 6: Advanced Settings")
    
    advanced = get_choice("Configure advanced settings?", 
                        ["Yes, customize advanced options", "No, use defaults"])
    
    if advanced == "Yes, customize advanced options":
        # Max images
        max_images = get_input("Maximum number of images to return", "50")
        try:
            config["output"]["max_images"] = int(max_images)
        except ValueError:
            config["output"]["max_images"] = 50
        
        # Minimum matches
        if config["content_rules"]["preferred_keywords"]:
            min_matches = get_input("Minimum total keyword matches required", "1")
            try:
                config["content_rules"]["min_keyword_matches"] = int(min_matches)
            except ValueError:
                config["content_rules"]["min_keyword_matches"] = 1
        
        # Description length
        quality_filter = get_choice("Filter by description quality?", 
                                  ["Yes, require detailed descriptions", "No, accept all lengths"])
        if quality_filter == "Yes, require detailed descriptions":
            config["filters"]["min_description_length"] = 100
    
    # Step 7: Save and run
    return finalize_and_run(config)


def finalize_and_run(config):
    """Save configuration and run the identification"""
    print_header("💾 Save and Run")
    
    print("Configuration created! Here's what we'll search for:")
    print()
    print(f"📝 Gallery: {config['gallery_name']}")
    print(f"📁 Scanning: {', '.join(config['sources']['directories'])}")
    
    if config['content_rules']['required_keywords']:
        print(f"🔍 Required: {', '.join(config['content_rules']['required_keywords'])}")
    
    if config['content_rules']['preferred_keywords']:
        print(f"⭐ Preferred: {', '.join(config['content_rules']['preferred_keywords'])}")
    
    if config['content_rules']['excluded_keywords']:
        print(f"🚫 Excluded: {', '.join(config['content_rules']['excluded_keywords'])}")
    
    print(f"📊 Max images: {config['output']['max_images']}")
    print()
    
    # Ask to save config
    save_config = get_choice("Would you like to save this configuration for reuse?", 
                           ["Yes, save it", "No, just run once"])
    
    config_file = None
    if save_config == "Yes, save it":
        # Generate filename from gallery name
        safe_name = "".join(c for c in config['gallery_name'] if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_name = safe_name.replace(' ', '_').lower()
        default_filename = f"{safe_name}.json"
        
        filename = get_input(f"Configuration filename", default_filename)
        if not filename.endswith('.json'):
            filename += '.json'
        
        config_file = SCRIPT_DIR / filename
        
        # Save the config
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            print(f"✅ Configuration saved to: {config_file}")
        except Exception as e:
            print(f"❌ Error saving configuration: {e}")
            config_file = None
    
    # Run the identification
    return run_identification(config_file, config['sources']['directories'], config['gallery_name'], config)


def run_identification(config_file, scan_dirs, gallery_name, config_dict=None):
    """Run the gallery content identification tool"""
    print_header("🔍 Running Gallery Identification")
    
    print(f"🎯 Searching for: {gallery_name}")
    print(f"📁 Scanning: {', '.join(scan_dirs)}")
    print()
    print("This may take a few minutes depending on how many images you have...")
    print()
    
    # Generate output filename
    safe_name = "".join(c for c in gallery_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
    safe_name = safe_name.replace(' ', '_').lower()
    output_file = f"{safe_name}_results.json"
    
    # Build command
    script_path = SCRIPT_DIR / "identify_gallery_content.py"
    
    try:
        if config_file and config_file.exists():
            # Use config file
            cmd = [sys.executable, str(script_path), 
                   "--config", str(config_file), 
                   "--output", output_file]
        else:
            # Use config_dict to build CLI command
            cmd = [sys.executable, str(script_path)]
            
            if config_dict:
                cmd.extend(["--name", config_dict["gallery_name"]])
                
                for directory in config_dict["sources"]["directories"]:
                    cmd.extend(["--scan", directory])
                
                if config_dict["content_rules"]["required_keywords"]:
                    cmd.extend(["--required", ",".join(config_dict["content_rules"]["required_keywords"])])
                
                if config_dict["content_rules"]["preferred_keywords"]:
                    cmd.extend(["--keywords", ",".join(config_dict["content_rules"]["preferred_keywords"])])
                
                if config_dict["content_rules"]["excluded_keywords"]:
                    cmd.extend(["--exclude", ",".join(config_dict["content_rules"]["excluded_keywords"])])
                
                cmd.extend(["--min-matches", str(config_dict["content_rules"]["min_keyword_matches"])])
                cmd.extend(["--max-images", str(config_dict["output"]["max_images"])])
                
                if config_dict["filters"]["min_description_length"] > 0:
                    cmd.extend(["--min-length", str(config_dict["filters"]["min_description_length"])])
            
            cmd.extend(["--output", output_file])
        
        # Run the command
        print("Running identification tool...")
        result = subprocess.run(cmd, cwd=str(SCRIPT_DIR), capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Success! Results saved to: {output_file}")
            
            # Try to show summary
            results_path = SCRIPT_DIR / output_file
            if results_path.exists():
                try:
                    with open(results_path, 'r', encoding='utf-8') as f:
                        results = json.load(f)
                    
                    candidates = results.get('candidates', [])
                    print(f"📊 Found {len(candidates)} matching images!")
                    
                    if candidates:
                        print(f"🏆 Top match: {candidates[0].get('filename', 'Unknown')} (score: {candidates[0].get('score', 0)})")
                        
                        if len(candidates) >= 5:
                            print(f"📈 Score range: {candidates[0].get('score', 0)} to {candidates[-1].get('score', 0)}")
                
                except Exception as e:
                    print(f"Results saved but couldn't read summary: {e}")
            
            print()
            print("🎉 Gallery identification complete!")
            print()
            print("Next steps:")
            print(f"  1. Review the results in: {output_file}")
            print("  2. Copy your favorite images to a gallery directory")
            print("  3. Use the existing ImageGallery tools to build your gallery")
            print()
            
            # Offer to create IDW file for visual review
            print("📋 BONUS: Create IDW workspace for visual review?")
            print()
            print("This creates a workspace file (.idw) that can be opened in")
            print("ImageDescriber or Viewer to visually browse your identified")
            print("images with all their descriptions included.")
            print()
            
            while True:
                create_idw = input("Create IDW workspace? [y/N]: ").strip().lower()
                if create_idw in ['', 'n', 'no']:
                    break
                elif create_idw in ['y', 'yes']:
                    try:
                        print()
                        print("🔨 Creating IDW workspace...")
                        # Use the first scan directory as workflows directory
                        workflows_dir = scan_dirs[0] if scan_dirs else "."
                        idw_result = create_idw_workspace(output_file, workflows_dir)
                        if idw_result:
                            print("✅ IDW workspace created successfully!")
                            print(f"   File: {idw_result}")
                            print()
                            print("To view: Open this .idw file in ImageDescriber or Viewer")
                            print("You can now visually browse all identified images with descriptions!")
                        else:
                            print("❌ Failed to create IDW workspace")
                    except Exception as e:
                        print(f"❌ Error creating IDW workspace: {e}")
                    break
                else:
                    print("Please enter 'y' for yes or 'n' for no.")
            
        else:
            print(f"❌ Error running identification tool:")
            print(result.stderr)
            print()
            print("Common issues:")
            print("  • Python not installed or not in PATH")
            print("  • Scan directories not accessible")
            print("  • No workflow results found")
            
        return 'DONE'
        
    except Exception as e:
        print(f"❌ Error running identification: {e}")
        return 'ERROR'


def main():
    """Main wizard entry point"""
    try:
        while True:
            result = welcome_screen()
            
            if result == 'EXIT':
                break
            elif result == 'EXAMPLES':
                result = show_examples()
                if result == 'DONE' or result == 'ERROR':
                    break
                elif result == 'BACK':
                    continue
                elif result == 'WIZARD':
                    result = wizard_mode()
                    if result == 'DONE' or result == 'ERROR':
                        break
            elif result == 'WIZARD':
                result = wizard_mode()
                if result == 'DONE' or result == 'ERROR':
                    break
    
    except KeyboardInterrupt:
        print("\n\n👋 Gallery wizard cancelled by user. Goodbye!")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("Please report this issue if it persists.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())