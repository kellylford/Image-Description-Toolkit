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
    """Get the base directory (project root) where resources are located."""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable - exe is in dist/ or install dir
        # Resources (scripts/, analysis/) are bundled in same location
        return Path(sys.executable).parent
    else:
        # Running as script from idt/ directory - go up to project root
        return Path(__file__).parent.parent


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller bundle."""
    if getattr(sys, 'frozen', False):
        # PyInstaller bundle - files are in sys._MEIPASS
        base_path = Path(sys._MEIPASS)
    else:
        # Development - files are relative to project root (one level up from idt/)
        base_path = Path(__file__).parent.parent
    
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

    # Normalize alias: 'describe' is identical to 'workflow'
    if command == 'describe':
        command = 'workflow'
        sys.argv[1] = 'workflow'

    # Normalize alias: 'redescribe <wf_dir> [opts]' -> 'workflow --redescribe <wf_dir> [opts]'
    elif command == 'redescribe':
        rest = sys.argv[2:]
        if '--help' in rest or '-h' in rest:
            sys.argv = [sys.argv[0], 'workflow'] + rest
        elif rest and not rest[0].startswith('-'):
            sys.argv = [sys.argv[0], 'workflow', '--redescribe', rest[0]] + rest[1:]
        else:
            sys.argv = [sys.argv[0], 'workflow', '--redescribe'] + rest
        command = 'workflow'

    # Update console title based on command
    title_map = {
        'guideme': 'IDT - Guided Workflow',
        'workflow': 'IDT - Describing Images',
        'stats': 'IDT - Analyzing Statistics',
        'contentreview': 'IDT - Content Review',
        'combinedescriptions': 'IDT - Combining Descriptions',
        'results-list': 'IDT - Listing Results',
        'check-models': 'IDT - Checking Models',
        'manage-models': 'IDT - Managing Models',
        'prompt-list': 'IDT - Listing Prompts',
        'extract-frames': 'IDT - Extracting Video Frames',
        'describe-video': 'IDT - Describing Videos',
        'convert-images': 'IDT - Converting Images',
        'descriptions-to-html': 'IDT - Generating HTML',
        'version': 'IDT - Version Info',
        'help': 'IDT - Help'
    }
    
    if command in title_map:
        set_console_title(title_map[command])
    
    # Route to appropriate script
    if command == 'workflow':
        # Add default output directory if not specified
        args = sys.argv[2:]
        if '--output-dir' not in args and '-o' not in args and '--resume' not in args and '--redescribe' not in args:
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
                sys.argv = ['idt workflow'] + args  # Use modified args with default output dir
                
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
                sys.argv = ['idt stats'] + sys.argv[2:]
                
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
                sys.argv = ['idt contentreview'] + sys.argv[2:]
                
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

                # Try loading from the filesystem first so that a .py file placed
                # alongside the exe in analysis/ overrides the bundled module.
                # (The frozen importer would otherwise always win over sys.path.)
                _combine_mod = None
                _override_py = Path(sys.executable).parent / 'analysis' / 'combine_workflow_descriptions.py'
                if _override_py.exists():
                    import importlib.util as _ilu
                    _spec = _ilu.spec_from_file_location(
                        'combine_workflow_descriptions', _override_py,
                        submodule_search_locations=[]
                    )
                    _combine_mod = _ilu.module_from_spec(_spec)
                    _spec.loader.exec_module(_combine_mod)

                if _combine_mod is None:
                    import combine_workflow_descriptions as _combine_mod

                combine_workflow_descriptions = _combine_mod

                # Set up sys.argv for the combine script
                original_argv = sys.argv[:]
                sys.argv = ['idt combinedescriptions'] + sys.argv[2:]

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
                sys.argv = ['idt check-models'] + sys.argv[2:]
                
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
                sys.argv = ['idt results-list'] + sys.argv[2:]
                
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
                sys.argv = ['idt prompt-list'] + sys.argv[2:]
                
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
                sys.argv = ['idt extract-frames'] + sys.argv[2:]
                
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
    
    elif command == 'describe-video':
        # Generate AI description for videos
        if getattr(sys, 'frozen', False):
            # Running as executable - import directly
            try:
                # Add both scripts and imagedescriber directories to path
                scripts_path = get_resource_path('scripts')
                imagedescriber_path = get_resource_path('imagedescriber')
                
                if str(scripts_path) not in sys.path:
                    sys.path.insert(0, str(scripts_path))
                if str(imagedescriber_path) not in sys.path:
                    sys.path.insert(0, str(imagedescriber_path))
                
                import video_describer
                
                # Set up sys.argv for the video describer script
                original_argv = sys.argv[:]
                sys.argv = ['idt describe-video'] + sys.argv[2:]
                
                try:
                    return video_describer.main()
                except SystemExit as e:
                    return e.code if e.code is not None else 0
                finally:
                    sys.argv = original_argv
                    
            except ImportError as e:
                print(f"Error: Could not import video_describer module: {e}")
                import traceback
                traceback.print_exc()
                return 1
            except Exception as e:
                print(f"Error running video describer: {e}")
                import traceback
                traceback.print_exc()
                return 1
        else:
            # Running as script - use subprocess
            describer_script = get_resource_path('scripts/video_describer.py')
            
            if not describer_script.exists():
                print(f"Error: Video describer script not found at {describer_script}")
                return 1
            
            import subprocess
            args = sys.argv[2:]
            cmd = [sys.executable, str(describer_script)] + args
            result = subprocess.run(cmd, cwd=str(describer_script.parent))
            return result.returncode
    
    elif command == 'version' or command == '--version' or command == '-v':
        # Show version (with build number and git info)
        try:
            # Ensure scripts path is available for imports
            scripts_path = get_resource_path('scripts')
            if str(scripts_path) not in sys.path:
                sys.path.insert(0, str(scripts_path))
            from versioning import get_full_version, get_git_info, is_frozen
            full = get_full_version()
            sha, dirty = get_git_info()
            mode = 'Frozen' if is_frozen() else 'Dev'
            print(f"Image Description Toolkit {full}")
            print(f"Commit: {sha or 'unknown'}{' (dirty)' if dirty else ''}")
            print(f"Mode: {mode}")
            return 0
        except Exception:
            # Fallback to plain VERSION file if anything goes wrong
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
                sys.argv = ['idt descriptions-to-html'] + sys.argv[2:]
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
                sys.argv = ['idt convert-images'] + sys.argv[2:]
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
                sys.argv = ['idt guideme'] + sys.argv[2:]
                
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

    elif command == 'manage-models':
        # Manage AI models: list, install, remove, info, recommend
        if getattr(sys, 'frozen', False):
            try:
                models_path = get_resource_path('models')
                if str(models_path) not in sys.path:
                    sys.path.insert(0, str(models_path))

                import manage_models

                original_argv = sys.argv[:]
                sys.argv = ['idt manage-models'] + sys.argv[2:]

                try:
                    return manage_models.main()
                except SystemExit as e:
                    return e.code if e.code is not None else 0
                finally:
                    sys.argv = original_argv

            except ImportError as e:
                print(f"Error: Could not import manage_models module: {e}")
                return 1
            except Exception as e:
                print(f"Error running manage_models: {e}")
                return 1
        else:
            manage_script = get_resource_path('models/manage_models.py')

            if not manage_script.exists():
                print(f"Error: Manage models script not found at {manage_script}")
                return 1

            import subprocess
            args = sys.argv[2:]
            cmd = [sys.executable, str(manage_script)] + args
            result = subprocess.run(cmd, cwd=str(manage_script.parent))
            return result.returncode

    elif command == 'help' or command == '--help' or command == '-h':
        print_usage()
        return 0

    elif command.startswith('-') and len(command) == 2 and command[1].isalpha():
        # Python interpreter flags (e.g. -B, -c, -m, -s, -S, -E, -u) passed by
        # multiprocessing.resource_tracker when it tries to respawn using
        # sys.executable (which is this frozen binary in frozen mode).
        # Silently exit — these are not real IDT commands.
        return 0

    else:
        print(f"Error: Unknown command '{command}'")
        print()
        print_usage()
        return 1


def print_usage():
    """Print usage information."""
    exe_name = 'idt.exe' if getattr(sys, 'frozen', False) else (Path(sys.argv[0]).name or 'idt')
    base_call = exe_name
    print(f"""
Image Description Toolkit - Unified CLI

USAGE:
    {base_call} <command> [options]

COMMANDS:
    guideme               Interactive wizard to build and run a workflow
    workflow              Run image description workflow
    describe              Alias for workflow (e.g. idt describe ./photos)
    redescribe            Shorthand for workflow --redescribe (re-describe with new model)
    stats                 Analyze workflow performance statistics
    contentreview         Analyze description content and quality
    combinedescriptions   Combine descriptions from multiple workflows
    manage-models         Install, remove, and list AI models
    results-list          List available workflow results
    check-models          Check available AI models (Ollama, OpenAI, Claude)
    prompt-list           List available prompt styles
    extract-frames        Extract frames from video files
    describe-video        Generate an AI description for a standalone video file
    convert-images        Convert HEIC/HEIF images to JPEG
    descriptions-to-html  Generate HTML report from a workflow descriptions file
    version               Show version information
    help                  Show this help message

  Note: ImageDescriber is a standalone GUI application (ImageDescriber.exe /
  ImageDescriber.app). Open it directly from your installation folder or Applications.
  Viewer Mode is built into ImageDescriber — use it to browse workflow results.

WORKFLOW OPTIONS (idt workflow):
    input_source                                  Input directory or URL
                                                  (optional with --resume/--redescribe)
    --output-dir, -o <dir>                        Output directory (default: Descriptions)
    --provider <name>                             AI provider: ollama, openai, claude,
                                                  huggingface, mlx (default: ollama)
    --model <name>                                AI model name (e.g. llava, gpt-4o,
                                                  claude-opus-4-5)
    --prompt-style <style>                        Prompt style (see 'idt prompt-list')
    --steps <list>                                Comma-separated steps
                                                  (default: video,convert,describe,html)
    --resume, -r <workflow_dir>                   Resume an interrupted workflow
    --redescribe <workflow_dir>                   Re-describe images from an existing
                                                  workflow with different AI settings
    --preserve-descriptions                       When resuming, skip re-describing if
                                                  already substantially complete
    --link-images                                 When redescribing, use symlinks/hardlinks
                                                  instead of copying images (saves space)
    --force-copy                                  When redescribing, always copy images
                                                  even if linking is available
    --timeout <seconds>                           Ollama request timeout in seconds
                                                  (default: 90; increase for slow hardware)
    --name <name>                                 Custom identifier appended to the
                                                  workflow directory name
    --api-key-file <file>                         File containing API key (OpenAI or Claude)
    --download, -d <url>                          Download images from a URL before describing
    --min-size <size>                             Minimum image size filter for downloads
                                                  (e.g. 100KB, 1MB)
    --max-images <n>                              Maximum number of images to download
    --url <url>                                   URL to download from (alternative to
                                                  providing URL as positional input_source)
    --no-alt-text                                 Exclude website alt text from descriptions
    --metadata / --no-metadata                    Enable/disable metadata extraction
                                                  (default: enabled)
    --no-geocode                                  Disable reverse geocoding
    --geocode-cache <file>                        Geocoding cache file
                                                  (default: geocode_cache.json)
    --dry-run                                     Show what would be done without executing
    --batch                                       Non-interactive mode (skip prompts)
    --progress-status                             Show live INFO log updates in console
    --show-descriptions <on|off>                  Print each AI description to the console
                                                  as it is generated (default: off)
    --view-results                                After completion, print results path and
                                                  ImageDescriber viewing instructions
    --verbose, -v                                 Enable verbose logging
    --config-workflow, --config-wf <file>         Workflow orchestration config
                                                  (default: workflow_config.json)
    --config-image-describer, --config-id <file>  Image describer config (prompts, AI,
                                                  metadata)
    --config-video <file>                         Video extraction config

VIDEO EXTRACTION OPTIONS (idt extract-frames):
    input                                     Video file or directory containing videos
    --output-dir <dir>                        Output directory for extracted frames
    --time <seconds>                          Time interval mode: one frame every N seconds
    --scene <threshold>                       Scene change mode: threshold 0-100, lower =
                                              more sensitive (e.g. --scene 30).
                                              Mutually exclusive with --time.
    --config-video, --config, -c <file>       Video config file
                                              (default: video_frame_extractor_config.json)
    --log-dir <dir>                           Directory for log files
    --create-config                           Create a default config file and exit
    --quiet                                   Suppress console output

    Supported formats: .mp4, .avi, .mkv, .mov, .wmv, .flv, .webm,
                       .m4v, .mpg, .mpeg, .3gp, .3g2, .mts, .m2ts

VIDEO DESCRIPTION OPTIONS (idt describe-video):
    video [video ...]                         One or more video files to describe
    --provider <name>                         AI provider: ollama, openai, claude
                                              (default: ollama)
    --model <name>                            Model name (default: llava)
    --prompt <text>                           Custom description prompt
    --frames <n>                              Number of frames to extract (default: 5)
    --mode <mode>                             Frame selection: key_frames, uniform,
                                              scene_change (default: key_frames)
    --output, -o <file>                       Output file (.txt or .json)
    --config, -c <file>                       Config file path
    --verbose, -v                             Enable verbose logging

CONVERT IMAGES OPTIONS (idt convert-images):
    input                                     HEIC/HEIF file or directory to convert
    --output, -o <path>                       Output file or directory
                                              (default: 'converted' subdirectory)
    --recursive, -r                           Process subdirectories recursively
    --quality, -q <1-100>                     JPEG quality (default: 95)
    --no-metadata                             Don't preserve metadata in converted files
    --log-dir <dir>                           Directory for log files
    --verbose, -v                             Enable verbose logging
    --quiet                                   Suppress console output

DESCRIPTIONS TO HTML OPTIONS (idt descriptions-to-html):
    input_file                                Descriptions text file
                                              (default: image_descriptions.txt)
    output_file                               Output HTML file (default: input file
                                              with .html extension)
    --title <text>                            Title for the HTML page
                                              (default: 'Image Descriptions')
    --full                                    Include full metadata details per image
    --log-dir <dir>                           Directory for log files
    --verbose                                 Enable verbose output

COMBINE DESCRIPTIONS OPTIONS (idt combinedescriptions):
    --input-dir <dir>                         Directory containing workflow folders
                                              (default: auto-detect)
    --output <file>                           Output filename
                                              (default: analysis/results/combineddescriptions.csv)
    --format csv|tsv|atsv                     Output format (default: csv; opens in Excel)
    --sort name|date                          Sort by filename or EXIF date (default: date)

STATS OPTIONS (idt stats):
    --input-dir <dir>                         Directory containing workflow folders
                                              (default: Descriptions/)
    --csv-output <file>                       CSV output file
                                              (default: analysis/results/workflow_timing_stats.csv)
    --json-output <file>                      JSON output file
                                              (default: analysis/results/workflow_statistics.json)
    --text-output <file>                      Text report file
                                              (default: analysis/results/workflow_report.txt)

CONTENT REVIEW OPTIONS (idt contentreview):
    --input <file>                            Combined descriptions CSV to review
                                              (default: combineddescriptions.csv)
    --output <file>                           Output CSV
                                              (default: analysis/results/description_content_analysis.csv)

CHECK MODELS OPTIONS (idt check-models):
    --provider ollama|ollama-cloud|openai|claude   Check only a specific provider
    --verbose, -v                             Show detailed model information
    --json                                    Output as JSON (for scripting)

RESULTS LIST OPTIONS (idt results-list):
    --input-dir, -i <dir>                     Directory containing workflow results
                                              (default: auto-detect)
    --output, -o <file>                       Output CSV (default: workflow_results.csv)
    --sort-by name|timestamp|provider|model   Sort field (default: timestamp)
    --absolute-paths                          Use absolute paths in output

PROMPT LIST OPTIONS (idt prompt-list):
    --config-image-describer <file>           Custom image_describer_config.json
      (aliases: --config-id, --config, -c)
    --verbose, -v                             Show full prompt text for each style

MANAGE MODELS OPTIONS (idt manage-models <subcommand>):
    list                                      List all known models
      --installed                             Show only installed models
      --provider <name>                       Filter by provider (ollama, openai,
                                              claude, huggingface)
    install <model>                           Install an Ollama model by name
      --recommended                           Install all recommended Ollama models
    remove <model>                            Remove an installed Ollama model
    info <model>                              Show information about a model
    recommend                                 Show recommended models for this system

EXAMPLES:
    # Interactive guided workflow (recommended for beginners)
    {base_call} guideme

    # Run workflow with Ollama (local)
    {base_call} workflow photos/ --provider ollama --model llava

    # Run workflow with OpenAI
    {base_call} workflow photos/ --provider openai --model gpt-4o

    # Run workflow with Claude
    {base_call} workflow photos/ --provider claude --model claude-opus-4-5

    # Run only the describe step (skip video extraction and HTML)
    {base_call} workflow photos/ --steps describe

    # Resume an interrupted workflow
    {base_call} workflow --resume wf_2025-01-15_143022_llava_Simple

    # Re-describe with a different model
    {base_call} workflow --redescribe wf_2025-01-15_143022_llava_Simple --model gpt-4o
    {base_call} redescribe wf_2025-01-15_143022_llava_Simple --model gpt-4o

    # Download images from a website and describe them
    {base_call} workflow --download https://example.com/gallery --provider ollama

    # Extract frames from a video every 5 seconds
    {base_call} extract-frames video.mp4 --time 5 --output-dir frames/

    # Extract frames using scene change detection
    {base_call} extract-frames video.mp4 --scene 30 --output-dir frames/

    # Extract frames from all videos in a directory
    {base_call} extract-frames videos/ --time 10 --output-dir frames/

    # Generate AI description for a video
    {base_call} describe-video video.mp4 --provider ollama --model llava

    # Describe a video with more frames and a custom prompt
    {base_call} describe-video video.mp4 --frames 10 --prompt "Describe the key events"

    # Convert HEIC images to JPEG
    {base_call} convert-images photos/

    # Convert HEIC images recursively with custom quality
    {base_call} convert-images photos/ --recursive --quality 90

    # Generate HTML report from a workflow's descriptions file
    {base_call} descriptions-to-html wf_2025-01-15_143022_llava_Simple/image_descriptions.txt

    # Analyze workflow statistics
    {base_call} stats

    # Analyze description content quality (run combinedescriptions first)
    {base_call} contentreview

    # Combine descriptions to CSV
    {base_call} combinedescriptions --output results.csv

    # List available workflow results
    {base_call} results-list
    {base_call} results-list --input-dir /path/to/Descriptions

    # Check available AI models
    {base_call} check-models
    {base_call} check-models --provider ollama --verbose

    # List available prompt styles
    {base_call} prompt-list
    {base_call} prompt-list --verbose

    # Manage AI models
    {base_call} manage-models list
    {base_call} manage-models list --installed
    {base_call} manage-models install llava:7b
    {base_call} manage-models recommend

NOTES:
    - Requires Ollama for local AI models (https://ollama.ai)
    - Requires API keys for OpenAI (OPENAI_API_KEY) and Anthropic (ANTHROPIC_API_KEY)
    - All commands support --help for their full option reference
    - Run 'idt guideme' for an interactive setup walkthrough

For detailed documentation, see the docs/ folder.
""")


if __name__ == '__main__':
    sys.exit(main())
