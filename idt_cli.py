#!/usr/bin/env python3
"""
Image Description Toolkit - Unified CLI Dispatcher
Creates a single executable interface for all toolkit commands.

This file ONLY routes commands to existing scripts - it doesn't modify any existing code.
"""
import sys
import os
from pathlib import Path


def get_base_dir():
    """Get the base directory where the executable or script is located."""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        # PyInstaller extracts to a temp directory, we need the real base
        return Path(sys.executable).parent
    else:
        # Running as script
        return Path(__file__).parent


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller bundle."""
    if getattr(sys, 'frozen', False):
        # PyInstaller bundle - files are in sys._MEIPASS
        base_path = Path(sys._MEIPASS)
    else:
        # Development - files are relative to this script
        base_path = Path(__file__).parent
    
    return base_path / relative_path


def main():
    """Main CLI dispatcher - routes commands to existing scripts."""
    
    # Get base directory
    base_dir = get_base_dir()
    
    # Debug information (remove this after testing)
    if '--debug-paths' in sys.argv:
        print(f"Base directory: {base_dir}")
        print(f"Current working directory: {os.getcwd()}")
        if getattr(sys, 'frozen', False):
            print(f"Running as PyInstaller executable")
            print(f"sys.executable: {sys.executable}")
            print(f"sys._MEIPASS: {getattr(sys, '_MEIPASS', 'Not available')}")
        else:
            print(f"Running as Python script")
        
        # List what's in the base directory
        try:
            print(f"Contents of base directory:")
            for item in base_dir.iterdir():
                print(f"  {item.name} ({'dir' if item.is_dir() else 'file'})")
        except Exception as e:
            print(f"Error listing base directory: {e}")
        
        # If PyInstaller, list what's in _MEIPASS
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            try:
                meipass = Path(sys._MEIPASS)
                print(f"Contents of _MEIPASS ({meipass}):")
                for item in meipass.iterdir():
                    print(f"  {item.name} ({'dir' if item.is_dir() else 'file'})")
            except Exception as e:
                print(f"Error listing _MEIPASS: {e}")
        
        return 0
    
    # Change to base directory so relative paths work
    os.chdir(base_dir)
    
    # Parse command
    if len(sys.argv) < 2:
        print_usage()
        return 1
    
    command = sys.argv[1]
    
    # Route to appropriate script
    if command == 'workflow':
        # For PyInstaller, we need to import and run the module directly
        if getattr(sys, 'frozen', False):
            # Running as executable - import the module directly
            try:
                # Add the scripts directory to Python path
                scripts_path = get_resource_path('scripts')
                if str(scripts_path) not in sys.path:
                    sys.path.insert(0, str(scripts_path))
                
                # Import workflow module
                import workflow
                
                # Set up sys.argv for the workflow script
                original_argv = sys.argv[:]
                sys.argv = ['workflow.py'] + sys.argv[2:]  # Remove 'workflow' command, keep the rest
                
                try:
                    # Run the workflow main function
                    return workflow.main()
                except SystemExit as e:
                    return e.code if e.code is not None else 0
                finally:
                    # Restore original argv
                    sys.argv = original_argv
                    
            except ImportError as e:
                print(f"Error: Could not import workflow module: {e}")
                return 1
            except Exception as e:
                print(f"Error running workflow: {e}")
                return 1
        else:
            # Running as script - use subprocess (development mode)
            scripts_dir = base_dir / 'scripts'
            workflow_script = scripts_dir / 'workflow.py'
            
            if not workflow_script.exists():
                print(f"Error: Workflow script not found at {workflow_script}")
                return 1
            
            import subprocess
            args = sys.argv[2:]
            cmd = [sys.executable, str(workflow_script)] + args
            result = subprocess.run(cmd, cwd=str(scripts_dir))
            return result.returncode
    
    elif command == 'analyze-stats' or command == 'stats':
        # Run stats analysis
        stats_script = get_resource_path('analysis/stats_analysis.py')
        
        if not stats_script.exists():
            print(f"Error: Stats analysis script not found at {stats_script}")
            return 1
        
        import subprocess
        args = sys.argv[2:]
        cmd = [sys.executable, str(stats_script)] + args
        result = subprocess.run(cmd, cwd=str(stats_script.parent))
        return result.returncode
    
    elif command == 'analyze-content' or command == 'content':
        # Run content analysis
        content_script = get_resource_path('analysis/content_analysis.py')
        
        if not content_script.exists():
            print(f"Error: Content analysis script not found at {content_script}")
            return 1
        
        import subprocess
        args = sys.argv[2:]
        cmd = [sys.executable, str(content_script)] + args
        result = subprocess.run(cmd, cwd=str(content_script.parent))
        return result.returncode
    
    elif command == 'combine':
        # Combine workflow descriptions
        combine_script = get_resource_path('analysis/combine_workflow_descriptions.py')
        
        if not combine_script.exists():
            print(f"Error: Combine script not found at {combine_script}")
            return 1
        
        import subprocess
        args = sys.argv[2:]
        cmd = [sys.executable, str(combine_script)] + args
        result = subprocess.run(cmd, cwd=str(combine_script.parent))
        return result.returncode
    
    elif command == 'check-models':
        # Check installed models
        if getattr(sys, 'frozen', False):
            # Running as executable - import directly
            try:
                models_path = get_resource_path('models')
                if str(models_path) not in sys.path:
                    sys.path.insert(0, str(models_path))
                
                import check_models
                
                original_argv = sys.argv[:]
                sys.argv = ['check_models.py'] + sys.argv[2:]
                
                try:
                    return check_models.main()
                except SystemExit as e:
                    return e.code if e.code is not None else 0
                finally:
                    sys.argv = original_argv
                    
            except ImportError as e:
                print(f"Error: Could not import check_models module: {e}")
                return 1
            except Exception as e:
                print(f"Error running check_models: {e}")
                return 1
        else:
            # Development mode - use subprocess
            check_script = get_resource_path('models/check_models.py')
            
            if not check_script.exists():
                print(f"Error: Check models script not found at {check_script}")
                return 1
            
            import subprocess
            args = sys.argv[2:]
            cmd = [sys.executable, str(check_script)] + args
            result = subprocess.run(cmd, cwd=str(check_script.parent))
            return result.returncode
    
    elif command == 'extract-frames':
        # Extract video frames
        extract_script = get_resource_path('scripts/video_frame_extractor.py')
        
        if not extract_script.exists():
            print(f"Error: Video frame extractor script not found at {extract_script}")
            return 1
        
        import subprocess
        args = sys.argv[2:]
        cmd = [sys.executable, str(extract_script)] + args
        result = subprocess.run(cmd, cwd=str(extract_script.parent))
        return result.returncode
    
    elif command == 'version' or command == '--version' or command == '-v':
        # Show version
        version_file = get_resource_path('VERSION')
        if version_file.exists():
            print(f"Image Description Toolkit v{version_file.read_text().strip()}")
        else:
            print("Image Description Toolkit (version unknown)")
        return 0
    
    elif command == 'help' or command == '--help' or command == '-h':
        print_usage()
        return 0
    
    else:
        print(f"Error: Unknown command '{command}'")
        print()
        print_usage()
        return 1


def print_usage():
    """Print usage information."""
    print("""
Image Description Toolkit - Unified CLI

USAGE:
    ImageDescriptionToolkit.exe <command> [options]

COMMANDS:
    workflow              Run image description workflow
    analyze-stats         Analyze workflow performance statistics
    analyze-content       Analyze description content and quality
    combine               Combine descriptions from multiple workflows
    check-models          Check installed Ollama models
    extract-frames        Extract frames from video files
    version               Show version information
    help                  Show this help message

EXAMPLES:
    # Run workflow with Ollama
    ImageDescriptionToolkit.exe workflow --provider ollama --model llava

    # Run workflow with Claude
    ImageDescriptionToolkit.exe workflow --provider claude --model claude-opus-4

    # Analyze statistics
    ImageDescriptionToolkit.exe analyze-stats

    # Analyze content quality
    ImageDescriptionToolkit.exe analyze-content

    # Combine descriptions to CSV
    ImageDescriptionToolkit.exe combine --output results.csv

    # Check available models
    ImageDescriptionToolkit.exe check-models

NOTES:
    - Requires Ollama to be installed for Ollama models
    - Requires API keys for OpenAI and Anthropic (set via environment variables)
    - All commands support --help for detailed options

For detailed documentation, see the docs/ folder.
""")


if __name__ == '__main__':
    sys.exit(main())
