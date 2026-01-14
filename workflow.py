#!/usr/bin/env python3
"""Workflow wrapper - forwards calls to scripts/workflow.py"""
import sys
import os

def get_resource_path(relative_path):
    """Get the path to a resource, handling PyInstaller bundles."""
    if getattr(sys, 'frozen', False):
        # Running as a PyInstaller bundle
        return os.path.join(sys._MEIPASS, relative_path)
    else:
        # Running from source
        base_path = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_path, relative_path)

def main():
    """Main entry point that handles both bundled and source execution."""
    original_cwd = os.getcwd()
    
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle - import directly
        scripts_path = get_resource_path('scripts')
        sys.path.insert(0, scripts_path)
        
        try:
            # Import and run the workflow module directly
            from scripts import workflow as workflow_module
            
            # Add original-cwd to args and run
            sys.argv = ['workflow.py', '--original-cwd', original_cwd] + sys.argv[1:]
            workflow_module.main()
        except Exception as e:
            print(f"Error running workflow: {e}")
            sys.exit(1)
    else:
        # Running from source - use subprocess
        import subprocess
        
        root_dir = os.path.dirname(os.path.abspath(__file__))
        scripts_dir = os.path.join(root_dir, "scripts")
        workflow_script = os.path.join(scripts_dir, "workflow.py")
        
        args_with_cwd = ['--original-cwd', original_cwd] + sys.argv[1:]
        cmd = [sys.executable, workflow_script] + args_with_cwd
        
        result = subprocess.run(cmd, cwd=scripts_dir)
        sys.exit(result.returncode)

if __name__ == "__main__":
    main()
