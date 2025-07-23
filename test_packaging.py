#!/usr/bin/env python3
"""
Test script to verify that the packaging setup works correctly.
This tests the core package functionality without requiring external dependencies like Ollama.
"""

import sys
import os
import tempfile
from pathlib import Path

def test_package_imports():
    """Test that all package components can be imported successfully."""
    print("Testing package imports...")
    
    try:
        import image_description_toolkit
        print("✓ Main package imported successfully")
        
        from image_description_toolkit.workflow import main as workflow_main
        print("✓ Workflow main function imported")
        
        from image_description_toolkit import ImageDescriber
        print("✓ ImageDescriber class imported")
        
        from image_description_toolkit import VideoFrameExtractor
        print("✓ VideoFrameExtractor class imported")
        
        from image_description_toolkit import convert_heic_to_jpg
        print("✓ convert_heic_to_jpg function imported")
        
        from image_description_toolkit import get_default_prompt_style
        print("✓ get_default_prompt_style function imported")
        
        print("✓ All package imports successful!")
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def test_package_metadata():
    """Test that package metadata is accessible."""
    print("\nTesting package metadata...")
    
    try:
        import image_description_toolkit
        
        assert hasattr(image_description_toolkit, '__version__')
        print(f"✓ Version: {image_description_toolkit.__version__}")
        
        assert hasattr(image_description_toolkit, '__author__')
        print(f"✓ Author: {image_description_toolkit.__author__}")
        
        assert hasattr(image_description_toolkit, '__description__')
        print(f"✓ Description: {image_description_toolkit.__description__}")
        
        print("✓ Package metadata accessible!")
        return True
        
    except (ImportError, AssertionError) as e:
        print(f"✗ Metadata error: {e}")
        return False

def test_configuration_files():
    """Test that configuration files are accessible."""
    print("\nTesting configuration files...")
    
    try:
        import image_description_toolkit
        package_path = Path(image_description_toolkit.__file__).parent
        
        config_files = [
            'workflow_config.json',
            'image_describer_config.json', 
            'video_frame_extractor_config.json'
        ]
        
        for config_file in config_files:
            config_path = package_path / config_file
            if config_path.exists():
                print(f"✓ Found {config_file}")
            else:
                print(f"✗ Missing {config_file}")
                return False
                
        print("✓ All configuration files found!")
        return True
        
    except Exception as e:
        print(f"✗ Configuration error: {e}")
        return False

def test_workflow_help():
    """Test that workflow help can be displayed."""
    print("\nTesting workflow help functionality...")
    
    try:
        from image_description_toolkit.workflow import main
        import sys
        from io import StringIO
        
        # Capture help output
        old_argv = sys.argv
        old_stdout = sys.stdout
        
        sys.argv = ['workflow', '--help']
        sys.stdout = StringIO()
        
        try:
            main()
        except SystemExit as e:
            # Help command exits with code 0
            if e.code == 0:
                help_output = sys.stdout.getvalue()
                if "Image Description Toolkit" in help_output:
                    print("✓ Workflow help displays correctly")
                    return True
                else:
                    print("✗ Help output missing expected content")
                    return False
            else:
                print(f"✗ Help command exited with code {e.code}")
                return False
        finally:
            sys.argv = old_argv
            sys.stdout = old_stdout
            
    except Exception as e:
        print(f"✗ Workflow help error: {e}")
        return False

def test_class_instantiation():
    """Test that main classes can be instantiated."""
    print("\nTesting class instantiation...")
    
    try:
        from image_description_toolkit import ImageDescriber, VideoFrameExtractor
        
        # Test ImageDescriber instantiation
        try:
            describer = ImageDescriber()
            print("✓ ImageDescriber can be instantiated")
        except Exception as e:
            print(f"⚠ ImageDescriber instantiation warning: {e}")
            # This might fail due to missing Ollama, which is expected
        
        # Test VideoFrameExtractor instantiation
        try:
            extractor = VideoFrameExtractor()
            print("✓ VideoFrameExtractor can be instantiated")
        except Exception as e:
            print(f"⚠ VideoFrameExtractor instantiation warning: {e}")
            
        return True
        
    except Exception as e:
        print(f"✗ Class instantiation error: {e}")
        return False

def main():
    """Run all tests."""
    print("=== Testing Image Description Toolkit Package ===\n")
    
    tests = [
        test_package_imports,
        test_package_metadata,
        test_configuration_files,
        test_workflow_help,
        test_class_instantiation,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")
            results.append(False)
    
    print("\n=== Test Results ===")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed! Package is ready for distribution.")
        return 0
    else:
        print("⚠ Some tests failed. Check output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())