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


def set_console_title(title):
    """Set the Windows console title."""
    if sys.platform == 'win32':
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleTitleW(title)
        except Exception:
            # Silently fail if unable to set title
            pass


def main():
    """Main CLI dispatcher - routes commands to existing scripts."""
    
    # Set console title on Windows
    set_console_title("IDT - Image Description Toolkit")
    
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
    
    # Store original working directory for user paths
    original_cwd = os.getcwd()
    
    # Parse command
    if len(sys.argv) < 2:
        print_usage()
        return 1
    
    command = sys.argv[1]
    
    # Update console title based on command
    title_map = {
        'guideme': 'IDT - Guided Workflow',
        'workflow': 'IDT - Describing Images',
        'viewer': 'IDT - Viewer',
        'view': 'IDT - Viewer',
        'prompteditor': 'IDT - Prompt Editor',
        'imagedescriber': 'IDT - Image Describer',
        'stats': 'IDT - Analyzing Statistics',
        'contentreview': 'IDT - Content Review',
        'combinedescriptions': 'IDT - Combining Descriptions',
        'results-list': 'IDT - Listing Results',
        'check-models': 'IDT - Checking Models',
        'prompt-list': 'IDT - Listing Prompts',
        'extract-frames': 'IDT - Extracting Video Frames',
        'convert-images': 'IDT - Converting Images',
        'version': 'IDT - Version Info',
        'help': 'IDT - Help'
    }
    
    if command in title_map:
        set_console_title(title_map[command])
    
    # Route to appropriate script
    if command == 'workflow':
        # Add default output directory if not specified
        args = sys.argv[2:]
        if '--output-dir' not in args and '-o' not in args and '--resume' not in args:
            # Insert default output directory
            args = ['--output-dir', 'Descriptions'] + args
        
        # Add original working directory for path resolution
        args = ['--original-cwd', original_cwd] + args
        
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
                sys.argv = ['workflow.py'] + args  # Use modified args with default output dir
                
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
            cmd = [sys.executable, str(workflow_script)] + args  # Use modified args
            result = subprocess.run(cmd, cwd=str(scripts_dir))
            return result.returncode
    
    elif command == 'image_describer' or (len(sys.argv) > 1 and sys.argv[1].endswith('image_describer.py')):
        # Handle image_describer command (called from workflow.py)
        if getattr(sys, 'frozen', False):
            # Running as executable - import directly
            try:
                scripts_path = get_resource_path('scripts')
                if str(scripts_path) not in sys.path:
                    sys.path.insert(0, str(scripts_path))
                
                import image_describer
                
                # Remove the script path from argv if it exists
                original_argv = sys.argv[:]
                if len(sys.argv) > 1 and sys.argv[1].endswith('image_describer.py'):
                    # Called as: executable.exe /path/to/image_describer.py args...
                    sys.argv = ['image_describer.py'] + sys.argv[2:]
                else:
                    # Called as: executable.exe image_describer args...
                    sys.argv = ['image_describer.py'] + sys.argv[2:]
                
                try:
                    return image_describer.main()
                except SystemExit as e:
                    return e.code if e.code is not None else 0
                finally:
                    sys.argv = original_argv
                    
            except ImportError as e:
                print(f"Error: Could not import image_describer module: {e}")
                return 1
            except Exception as e:
                print(f"Error running image_describer: {e}")
                return 1
        else:
            # Running as script - use subprocess (development mode)
            scripts_dir = base_dir / 'scripts'
            image_describer_script = scripts_dir / 'image_describer.py'
            
            if not image_describer_script.exists():
                print(f"Error: Image describer script not found at {image_describer_script}")
                return 1
            
            import subprocess
            # Remove the script path from args if it exists
            args = sys.argv[2:]
            if len(sys.argv) > 1 and sys.argv[1].endswith('image_describer.py'):
                args = sys.argv[2:]
            cmd = [sys.executable, str(image_describer_script)] + args
            result = subprocess.run(cmd, cwd=str(scripts_dir))
            return result.returncode
    
    elif command == 'stats':
        # Run stats analysis
        if getattr(sys, 'frozen', False):
            # Running as executable - import directly
            try:
                analysis_path = get_resource_path('analysis')
                if str(analysis_path) not in sys.path:
                    sys.path.insert(0, str(analysis_path))
                
                import stats_analysis
                
                # Set up sys.argv for the stats script
                original_argv = sys.argv[:]
                sys.argv = ['stats_analysis.py'] + sys.argv[2:]
                
                try:
                    return stats_analysis.main()
                except SystemExit as e:
                    return e.code if e.code is not None else 0
                finally:
                    sys.argv = original_argv
                    
            except ImportError as e:
                print(f"Error: Could not import stats_analysis module: {e}")
                return 1
            except Exception as e:
                print(f"Error running stats analysis: {e}")
                return 1
        else:
            # Running as script - use subprocess
            stats_script = get_resource_path('analysis/stats_analysis.py')
            
            if not stats_script.exists():
                print(f"Error: Stats analysis script not found at {stats_script}")
                return 1
            
            import subprocess
            args = sys.argv[2:]
            cmd = [sys.executable, str(stats_script)] + args
            result = subprocess.run(cmd, cwd=str(stats_script.parent))
            return result.returncode
    
    elif command == 'contentreview':
        # Run content analysis
        if getattr(sys, 'frozen', False):
            # Running as executable - import directly
            try:
                analysis_path = get_resource_path('analysis')
                if str(analysis_path) not in sys.path:
                    sys.path.insert(0, str(analysis_path))
                
                import content_analysis
                
                # Set up sys.argv for the content script
                original_argv = sys.argv[:]
                sys.argv = ['content_analysis.py'] + sys.argv[2:]
                
                try:
                    return content_analysis.main()
                except SystemExit as e:
                    return e.code if e.code is not None else 0
                finally:
                    sys.argv = original_argv
                    
            except ImportError as e:
                print(f"Error: Could not import content_analysis module: {e}")
                return 1
            except Exception as e:
                print(f"Error running content analysis: {e}")
                return 1
        else:
            # Running as script - use subprocess
            content_script = get_resource_path('analysis/content_analysis.py')
            
            if not content_script.exists():
                print(f"Error: Content analysis script not found at {content_script}")
                return 1
            
            import subprocess
            args = sys.argv[2:]
            cmd = [sys.executable, str(content_script)] + args
            result = subprocess.run(cmd, cwd=str(content_script.parent))
            return result.returncode
    
    elif command == 'combinedescriptions':
        # Combine workflow descriptions
        if getattr(sys, 'frozen', False):
            # Running as executable - import directly
            try:
                analysis_path = get_resource_path('analysis')
                if str(analysis_path) not in sys.path:
                    sys.path.insert(0, str(analysis_path))
                
                import combine_workflow_descriptions
                
                # Set up sys.argv for the combine script
                original_argv = sys.argv[:]
                sys.argv = ['combine_workflow_descriptions.py'] + sys.argv[2:]
                
                try:
                    return combine_workflow_descriptions.main()
                except SystemExit as e:
                    return e.code if e.code is not None else 0
                finally:
                    sys.argv = original_argv
                    
            except ImportError as e:
                print(f"Error: Could not import combine_workflow_descriptions module: {e}")
                return 1
            except Exception as e:
                print(f"Error running combine descriptions: {e}")
                return 1
        else:
            # Running as script - use subprocess
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
    
    elif command == 'results-list':
        # List available workflow results
        if getattr(sys, 'frozen', False):
            # Running as executable - import directly
            try:
                scripts_path = get_resource_path('scripts')
                if str(scripts_path) not in sys.path:
                    sys.path.insert(0, str(scripts_path))
                
                import list_results
                
                original_argv = sys.argv[:]
                sys.argv = ['list_results.py'] + sys.argv[2:]
                
                try:
                    return list_results.main()
                except SystemExit as e:
                    return e.code if e.code is not None else 0
                finally:
                    sys.argv = original_argv
                    
            except ImportError as e:
                print(f"Error: Could not import list_results module: {e}")
                return 1
            except Exception as e:
                print(f"Error running results-list: {e}")
                return 1
        else:
            # Development mode - use subprocess
            list_script = get_resource_path('scripts/list_results.py')
            
            if not list_script.exists():
                print(f"Error: Results list script not found at {list_script}")
                return 1
            
            import subprocess
            args = sys.argv[2:]
            cmd = [sys.executable, str(list_script)] + args
            result = subprocess.run(cmd, cwd=str(list_script.parent))
            return result.returncode
    
    elif command == 'prompt-list':
        # List available prompt styles
        if getattr(sys, 'frozen', False):
            # Running as executable - import directly
            try:
                scripts_path = get_resource_path('scripts')
                if str(scripts_path) not in sys.path:
                    sys.path.insert(0, str(scripts_path))
                
                import list_prompts
                
                original_argv = sys.argv[:]
                sys.argv = ['list_prompts.py'] + sys.argv[2:]
                
                try:
                    return list_prompts.main()
                except SystemExit as e:
                    return e.code if e.code is not None else 0
                finally:
                    sys.argv = original_argv
                    
            except ImportError as e:
                print(f"Error: Could not import list_prompts module: {e}")
                return 1
            except Exception as e:
                print(f"Error running prompt-list: {e}")
                return 1
        else:
            # Development mode - use subprocess
            list_script = get_resource_path('scripts/list_prompts.py')
            
            if not list_script.exists():
                print(f"Error: Prompt list script not found at {list_script}")
                return 1
            
            import subprocess
            args = sys.argv[2:]
            cmd = [sys.executable, str(list_script)] + args
            result = subprocess.run(cmd, cwd=str(list_script.parent))
            return result.returncode
    
    elif command == 'extract-frames':
        # Extract video frames
        if getattr(sys, 'frozen', False):
            # Running as executable - import directly
            try:
                scripts_path = get_resource_path('scripts')
                if str(scripts_path) not in sys.path:
                    sys.path.insert(0, str(scripts_path))
                
                import video_frame_extractor
                
                # Set up sys.argv for the video frame extractor script
                original_argv = sys.argv[:]
                sys.argv = ['video_frame_extractor.py'] + sys.argv[2:]
                
                try:
                    return video_frame_extractor.main()
                except SystemExit as e:
                    return e.code if e.code is not None else 0
                finally:
                    sys.argv = original_argv
                    
            except ImportError as e:
                print(f"Error: Could not import video_frame_extractor module: {e}")
                return 1
            except Exception as e:
                print(f"Error running video frame extractor: {e}")
                return 1
        else:
            # Running as script - use subprocess
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

    elif command == 'descriptions-to-html':
        # Generate HTML from descriptions (descriptions_to_html.py)
        if getattr(sys, 'frozen', False):
            try:
                scripts_path = get_resource_path('scripts')
                if str(scripts_path) not in sys.path:
                    sys.path.insert(0, str(scripts_path))
                import descriptions_to_html as dth
                # Rebuild argv: remove command token
                original_argv = sys.argv[:]
                sys.argv = ['descriptions_to_html.py'] + sys.argv[2:]
                try:
                    return dth.main()
                except SystemExit as e:
                    return e.code if e.code is not None else 0
                finally:
                    sys.argv = original_argv
            except ImportError as e:
                print(f"Error: Could not import descriptions_to_html module: {e}")
                return 1
        else:
            script_path = get_resource_path('scripts/descriptions_to_html.py')
            if not script_path.exists():
                print(f"Error: descriptions_to_html.py not found at {script_path}")
                return 1
            import subprocess
            args = sys.argv[2:]
            cmd = [sys.executable, str(script_path)] + args
            result = subprocess.run(cmd, cwd=str(script_path.parent))
            return result.returncode
    
    elif command == 'convert-images':
        # Convert HEIC images to JPG (ConvertImage.py)
        if getattr(sys, 'frozen', False):
            try:
                scripts_path = get_resource_path('scripts')
                if str(scripts_path) not in sys.path:
                    sys.path.insert(0, str(scripts_path))
                import ConvertImage as ci
                # Rebuild argv: remove command token
                original_argv = sys.argv[:]
                sys.argv = ['ConvertImage.py'] + sys.argv[2:]
                try:
                    return ci.main()
                except SystemExit as e:
                    return e.code if e.code is not None else 0
                finally:
                    sys.argv = original_argv
            except ImportError as e:
                print(f"Error: Could not import ConvertImage module: {e}")
                return 1
        else:
            script_path = get_resource_path('scripts/ConvertImage.py')
            if not script_path.exists():
                print(f"Error: ConvertImage.py not found at {script_path}")
                return 1
            import subprocess
            args = sys.argv[2:]
            cmd = [sys.executable, str(script_path)] + args
            result = subprocess.run(cmd, cwd=str(script_path.parent))
            return result.returncode
    
    elif command == 'guideme':
        # Interactive guided workflow
        if getattr(sys, 'frozen', False):
            # Running as executable - import directly
            try:
                scripts_path = get_resource_path('scripts')
                if str(scripts_path) not in sys.path:
                    sys.path.insert(0, str(scripts_path))
                
                import guided_workflow
                
                original_argv = sys.argv[:]
                sys.argv = ['guided_workflow.py'] + sys.argv[2:]
                
                try:
                    return guided_workflow.main()
                except SystemExit as e:
                    return e.code if e.code is not None else 0
                finally:
                    sys.argv = original_argv
                    
            except ImportError as e:
                print(f"Error: Could not import guided_workflow module: {e}")
                return 1
            except Exception as e:
                print(f"Error running guided workflow: {e}")
                return 1
        else:
            # Running as script - use subprocess
            guided_script = get_resource_path('scripts/guided_workflow.py')
            
            if not guided_script.exists():
                print(f"Error: Guided workflow script not found at {guided_script}")
                return 1
            
            import subprocess
            args = sys.argv[2:]
            cmd = [sys.executable, str(guided_script)] + args
            result = subprocess.run(cmd, cwd=str(guided_script.parent))
            return result.returncode
    
    elif command == 'viewer' or command == 'view':
        # Launch the viewer executable with optional directory argument
        import subprocess
        import platform
        
        # Detect architecture
        machine = platform.machine().lower()
        if machine in ('aarch64', 'arm64'):
            arch = 'arm64'
        else:
            arch = 'amd64'
        
        # Try multiple possible viewer locations
        viewer_names = [
            f'viewer_{arch}.exe',
            'viewer.exe',
            f'viewer/viewer_{arch}.exe',
            'viewer/viewer.exe',
            f'../viewer/viewer_{arch}.exe',
            '../viewer/viewer.exe',
        ]
        
        viewer_exe = None
        for name in viewer_names:
            candidate = base_dir / name
            if candidate.exists():
                viewer_exe = candidate
                break
        
        if not viewer_exe:
            print("Error: Viewer executable not found.")
            print(f"Looked in: {base_dir}")
            print(f"Expected: viewer_{arch}.exe or viewer.exe")
            print()
            print("The viewer must be built separately using:")
            print("  cd viewer")
            print("  build_viewer.bat")
            return 1
        
        # Get any additional arguments to pass to viewer
        viewer_args = sys.argv[2:]  # Everything after 'idt viewer'
        
        # Build command with arguments
        cmd = [str(viewer_exe)] + viewer_args
        
        # Launch viewer as separate process (detached)
        try:
            # On Windows, use CREATE_NO_WINDOW to launch GUI cleanly
            if sys.platform == 'win32':
                subprocess.Popen(cmd, 
                               creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS)
            else:
                subprocess.Popen(cmd)
            
            if viewer_args:
                print(f"Launched viewer: {viewer_exe.name} {' '.join(viewer_args)}")
            else:
                print(f"Launched viewer: {viewer_exe.name}")
            return 0
        except Exception as e:
            print(f"Error launching viewer: {e}")
            return 1
    
    elif command == 'prompteditor':
        # Launch the prompt editor executable
        import subprocess
        import platform
        
        # Detect architecture
        machine = platform.machine().lower()
        if machine in ('aarch64', 'arm64'):
            arch = 'arm64'
        else:
            arch = 'amd64'
        
        # Try multiple possible prompt editor locations
        editor_names = [
            f'prompteditor_{arch}.exe',
            'prompteditor.exe',
            f'prompteditor/prompteditor_{arch}.exe',
            'prompteditor/prompteditor.exe',
            f'../prompteditor/prompteditor_{arch}.exe',
            '../prompteditor/prompteditor.exe',
        ]
        
        editor_exe = None
        for name in editor_names:
            candidate = base_dir / name
            if candidate.exists():
                editor_exe = candidate
                break
        
        if not editor_exe:
            print("Error: Prompt Editor executable not found.")
            print(f"Looked in: {base_dir}")
            print(f"Expected: prompteditor_{arch}.exe or prompteditor.exe")
            print()
            print("The prompt editor must be built separately using:")
            print("  cd prompt_editor")
            print("  build_prompt_editor.bat")
            return 1
        
        # Launch prompt editor as separate process (detached)
        try:
            # On Windows, use CREATE_NO_WINDOW to launch GUI cleanly
            if sys.platform == 'win32':
                subprocess.Popen([str(editor_exe)], 
                               creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS)
            else:
                subprocess.Popen([str(editor_exe)])
            
            print(f"Launched prompt editor: {editor_exe.name}")
            return 0
        except Exception as e:
            print(f"Error launching prompt editor: {e}")
            return 1
    
    elif command == 'imagedescriber':
        # Launch the image describer GUI executable
        import subprocess
        import platform
        
        # Detect architecture
        machine = platform.machine().lower()
        if machine in ('aarch64', 'arm64'):
            arch = 'arm64'
        else:
            arch = 'amd64'
        
        # Try multiple possible image describer locations
        describer_names = [
            f'imagedescriber_{arch}.exe',
            'imagedescriber.exe',
            f'imagedescriber/imagedescriber_{arch}.exe',
            'imagedescriber/imagedescriber.exe',
            f'../imagedescriber/imagedescriber_{arch}.exe',
            '../imagedescriber/imagedescriber.exe',
        ]
        
        describer_exe = None
        for name in describer_names:
            candidate = base_dir / name
            if candidate.exists():
                describer_exe = candidate
                break
        
        if not describer_exe:
            print("Error: Image Describer executable not found.")
            print(f"Looked in: {base_dir}")
            print(f"Expected: imagedescriber_{arch}.exe or imagedescriber.exe")
            print()
            print("The image describer GUI must be built separately using:")
            print("  cd imagedescriber")
            print("  build_imagedescriber.bat")
            return 1
        
        # Launch image describer as separate process (detached)
        try:
            # On Windows, use CREATE_NO_WINDOW to launch GUI cleanly
            if sys.platform == 'win32':
                subprocess.Popen([str(describer_exe)], 
                               creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS)
            else:
                subprocess.Popen([str(describer_exe)])
            
            print(f"Launched image describer: {describer_exe.name}")
            return 0
        except Exception as e:
            print(f"Error launching image describer: {e}")
            return 1
    
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
    exe_name = 'idt.exe' if getattr(sys, 'frozen', False) else (Path(sys.argv[0]).name or 'idt')
    # Normalize if user renamed the file (strip extension for examples)
    base_call = exe_name
    print(f"""
Image Description Toolkit - Unified CLI

USAGE:
    {base_call} <command> [options]

COMMANDS:
    guideme               Interactive wizard to build and run workflows
    workflow              Run image description workflow
    viewer (or view)      Launch the GUI viewer for browsing results
    prompteditor          Launch the prompt editor to manage prompts
    imagedescriber        Launch the image describer GUI
    stats                 Analyze workflow performance statistics
    contentreview         Analyze description content and quality
    combinedescriptions   Combine descriptions from multiple workflows
    results-list          List available workflow results with viewer commands
    check-models          Check installed Ollama models
    prompt-list           List available prompt styles
    extract-frames        Extract frames from video files
    convert-images        Convert HEIC images to JPG
    version               Show version information
    help                  Show this help message

EXAMPLES:
    # Interactive guided workflow (recommended for beginners)
    {base_call} guideme

    # Run workflow with Ollama
    {base_call} workflow --provider ollama --model llava

    # Launch viewer (empty)
    {base_call} viewer

    # Launch viewer with specific directory
    {base_call} viewer C:\\path\\to\\workflow_output

    # Launch viewer with directory picker
    {base_call} viewer --open

    # Launch prompt editor
    {base_call} prompteditor

    # Launch image describer GUI
    {base_call} imagedescriber

    # Run workflow with Claude
    {base_call} workflow --provider claude --model claude-opus-4

    # Analyze statistics
    {base_call} stats

    # Analyze content quality
    {base_call} contentreview

    # Combine descriptions to CSV
    {base_call} combinedescriptions --output results.csv

    # List available workflow results
    {base_call} results-list
    {base_call} results-list --input-dir c:\\path\\to\\descriptions

    # Check available models
    {base_call} check-models

    # List available prompt styles
    {base_call} prompt-list
    {base_call} prompt-list --verbose

NOTES:
    - Requires Ollama to be installed for Ollama models
    - Requires API keys for OpenAI and Anthropic (set via environment variables)
    - GUI tools (viewer, prompteditor, imagedescriber) must be built separately
    - All commands support --help for detailed options

For detailed documentation, see the docs/ folder.
""")


if __name__ == '__main__':
    sys.exit(main())
