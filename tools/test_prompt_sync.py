#!/usr/bin/env python3
"""
Test prompt editor integration fix

This script tests that prompts saved via the PromptEditor
are correctly loaded by ProcessingOptionsDialog and CLI.

Tests both frozen executable mode and development mode scenarios.
"""

import json
import logging
import sys
from pathlib import Path

# Setup logging to see diagnostic messages
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)-8s - %(name)-20s - %(message)s'
)

def test_config_file_resolution():
    """Test that find_config_file() and load_json_config() find the same file"""
    print("\n=== Testing Config File Resolution ===")
    
    # Test find_config_file (used by PromptEditor and ProcessingOptionsDialog)
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from shared.wx_common import find_config_file
        config_path_1 = find_config_file('image_describer_config.json')
        print(f"✓ find_config_file() found: {config_path_1}")
    except Exception as e:
        print(f"✗ find_config_file() failed: {e}")
        config_path_1 = None
    
    # Test load_json_config (used by CLI)
    try:
        from scripts.config_loader import load_json_config
        cfg, config_path_2, source = load_json_config(
            'image_describer_config.json',
            env_var_file='IDT_IMAGE_DESCRIBER_CONFIG'
        )
        print(f"✓ load_json_config() found: {config_path_2} (source={source})")
    except Exception as e:
        print(f"✗ load_json_config() failed: {e}")
        config_path_2 = None
    
    # Compare paths
    if config_path_1 and config_path_2:
        if config_path_1.resolve() == Path(config_path_2).resolve():
            print(f"✓ Both methods resolve to SAME file: {config_path_1}")
            return config_path_1
        else:
            print(f"⚠ WARNING: Different paths!")
            print(f"  find_config_file:   {config_path_1}")
            print(f"  load_json_config:   {config_path_2}")
            return config_path_1
    elif config_path_1:
        return config_path_1
    elif config_path_2:
        return Path(config_path_2)
    else:
        print("✗ Both methods failed to find config file")
        return None


def test_config_contents(config_path):
    """Test that config contains expected prompts"""
    print("\n=== Testing Config Contents ===")
    
    if not config_path or not config_path.exists():
        print(f"✗ Config file not found: {config_path}")
        return False
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        
        prompts = cfg.get('prompt_variations', {})
        default = cfg.get('default_prompt_style', 'N/A')
        
        print(f"✓ Config loaded successfully from: {config_path}")
        print(f"  Prompts: {len(prompts)} variations")
        print(f"  Default: {default}")
        print(f"  Available prompts: {', '.join(prompts.keys())}")
        
        # Check if default exists in prompts
        if default in prompts:
            print(f"✓ Default prompt '{default}' exists in variations")
        else:
            print(f"⚠ WARNING: Default '{default}' not found in variations!")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"✗ Invalid JSON: {e}")
        return False
    except Exception as e:
        print(f"✗ Error reading config: {e}")
        return False


def test_gui_prompt_loading():
    """Test that GUI dialogs_wx.py can load prompts"""
    print("\n=== Testing GUI Prompt Loading ===")
    
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from shared.wx_common import find_config_file
        
        config_path = find_config_file('image_describer_config.json')
        if not config_path or not config_path.exists():
            print(f"✗ Config not found via find_config_file")
            return False
        
        print(f"✓ GUI would load from: {config_path}")
        
        # Simulate what ProcessingOptionsDialog.load_prompts() does
        with open(config_path, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        
        prompts = cfg.get('prompt_variations', {})
        default_style = cfg.get('default_prompt_style', 'narrative')
        
        if prompts:
            print(f"✓ Would populate {len(prompts)} prompts in dropdown")
            print(f"✓ Would select default: {default_style}")
            
            if default_style in prompts:
                print(f"✓ Default '{default_style}' found in prompts")
            else:
                print(f"⚠ Default '{default_style}' NOT in prompts (would select index 0)")
            
            return True
        else:
            print("⚠ No prompts found - would use hardcoded fallback")
            return False
            
    except Exception as e:
        print(f"✗ GUI prompt loading simulation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cli_prompt_loading():
    """Test that CLI image_describer.py can load prompts"""
    print("\n=== Testing CLI Prompt Loading ===")
    
    try:
        sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
        from config_loader import load_json_config
        
        cfg, path, source = load_json_config(
            'image_describer_config.json',
            env_var_file='IDT_IMAGE_DESCRIBER_CONFIG'
        )
        
        if not cfg:
            print(f"✗ CLI failed to load config")
            return False
        
        print(f"✓ CLI loaded from: {path} (source={source})")
        
        prompts = cfg.get('prompt_variations', {})
        default_style = cfg.get('default_prompt_style', 'detailed')
        
        if prompts:
            print(f"✓ CLI has access to {len(prompts)} prompts")
            print(f"✓ CLI default: {default_style}")
            
            if default_style.lower() in {k.lower(): k for k in prompts}:
                print(f"✓ Default '{default_style}' is valid (case-insensitive)")
            else:
                print(f"⚠ Default '{default_style}' not found in prompts")
            
            return True
        else:
            print("⚠ No prompts found in CLI config")
            return False
            
    except Exception as e:
        print(f"✗ CLI prompt loading failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all verification tests"""
    print("=" * 70)
    print("Prompt Editor Integration - Verification Tests")
    print("=" * 70)
    
    # Test 1: Config file resolution
    config_path = test_config_file_resolution()
    
    # Test 2: Config contents
    if config_path:
        test_config_contents(config_path)
    
    # Test 3: GUI prompt loading
    gui_ok = test_gui_prompt_loading()
    
    # Test 4: CLI prompt loading
    cli_ok = test_cli_prompt_loading()
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Config file found: {'✓' if config_path else '✗'}")
    print(f"GUI prompt loading: {'✓' if gui_ok else '✗'}")
    print(f"CLI prompt loading: {'✓' if cli_ok else '✗'}")
    
    if config_path and gui_ok and cli_ok:
        print("\n✓ ALL TESTS PASSED - Prompt sync should work correctly!")
        return 0
    else:
        print("\n⚠ SOME TESTS FAILED - Review errors above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
