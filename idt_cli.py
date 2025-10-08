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
        return Path(sys.executable).parent
    else:
        # Running as script
        return Path(__file__).parent


def main():
    """Main CLI dispatcher - routes commands to existing scripts."""
    
    # Get base directory
    base_dir = get_base_dir()
    
    # Change to base directory so relative paths work
    os.chdir(base_dir)
    
    # Parse command
    if len(sys.argv) < 2:
        print_usage()
        return 1
    
    command = sys.argv[1]
    
    # Route to appropriate script
    if command == 'workflow':
        # Import and run workflow
        # The workflow.py wrapper already handles everything correctly
        import workflow
        # workflow.py runs as subprocess, so we just need to call it
        # Actually, let's call the scripts/workflow.py directly
        scripts_dir = base_dir / 'scripts'
        workflow_script = scripts_dir / 'workflow.py'
        
        import subprocess
        args = sys.argv[2:]  # Pass all args after 'workflow'
        original_cwd = os.getcwd()
        args_with_cwd = ['--original-cwd', original_cwd] + args
        
        cmd = [sys.executable, str(workflow_script)] + args_with_cwd
        result = subprocess.run(cmd, cwd=str(scripts_dir))
        return result.returncode
    
    elif command == 'analyze-stats' or command == 'stats':
        # Run stats analysis
        analysis_dir = base_dir / 'analysis'
        stats_script = analysis_dir / 'stats_analysis.py'
        
        import subprocess
        args = sys.argv[2:]
        cmd = [sys.executable, str(stats_script)] + args
        result = subprocess.run(cmd, cwd=str(analysis_dir))
        return result.returncode
    
    elif command == 'analyze-content' or command == 'content':
        # Run content analysis
        analysis_dir = base_dir / 'analysis'
        content_script = analysis_dir / 'content_analysis.py'
        
        import subprocess
        args = sys.argv[2:]
        cmd = [sys.executable, str(content_script)] + args
        result = subprocess.run(cmd, cwd=str(analysis_dir))
        return result.returncode
    
    elif command == 'combine':
        # Combine workflow descriptions
        analysis_dir = base_dir / 'analysis'
        combine_script = analysis_dir / 'combine_workflow_descriptions.py'
        
        import subprocess
        args = sys.argv[2:]
        cmd = [sys.executable, str(combine_script)] + args
        result = subprocess.run(cmd, cwd=str(analysis_dir))
        return result.returncode
    
    elif command == 'check-models':
        # Check installed models
        models_dir = base_dir / 'models'
        check_script = models_dir / 'check_models.py'
        
        import subprocess
        args = sys.argv[2:]
        cmd = [sys.executable, str(check_script)] + args
        result = subprocess.run(cmd, cwd=str(models_dir))
        return result.returncode
    
    elif command == 'extract-frames':
        # Extract video frames
        scripts_dir = base_dir / 'scripts'
        extract_script = scripts_dir / 'video_frame_extractor.py'
        
        import subprocess
        args = sys.argv[2:]
        cmd = [sys.executable, str(extract_script)] + args
        result = subprocess.run(cmd, cwd=str(scripts_dir))
        return result.returncode
    
    elif command == 'version' or command == '--version' or command == '-v':
        # Show version
        version_file = base_dir / 'VERSION'
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
