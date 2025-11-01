"""
Basic tests for IDT configuration system.

Tests critical configuration infrastructure: file existence, validity,
and basic resolution. Designed to work with run_unit_tests.py (no pytest fixtures).

See GitHub Issue #62 for comprehensive test coverage roadmap.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

# Import the modules we're testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from config_loader import resolve_config, load_json_config


class TestConfigFiles:
    """Test that the three main configuration files exist and are valid."""
    
    def test_workflow_config_exists_and_valid(self):
        """Test workflow_config.json exists and is valid JSON with required structure."""
        config_path = Path(__file__).parent.parent.parent / "scripts" / "workflow_config.json"
        
        assert config_path.exists(), "workflow_config.json must exist"
        
        with config_path.open('r') as f:
            config = json.load(f)
        
        # Verify required top-level structure
        assert "workflow" in config, "Must have 'workflow' section"
        assert "steps" in config["workflow"], "Must have 'steps' in workflow"
        assert "file_patterns" in config, "Must have 'file_patterns' section"
        assert "logging" in config, "Must have 'logging' section"
        
        # Verify all four workflow steps exist
        steps = config["workflow"]["steps"]
        required_steps = ["video_extraction", "image_conversion", "image_description", "html_generation"]
        for step in required_steps:
            assert step in steps, f"Must have '{step}' step"
        
        # Verify image_description step has config_file reference
        assert "config_file" in steps["image_description"], \
            "image_description step must reference config_file"
    
    def test_image_describer_config_exists_and_valid(self):
        """Test image_describer_config.json exists and is valid JSON with required structure."""
        config_path = Path(__file__).parent.parent.parent / "scripts" / "image_describer_config.json"
        
        assert config_path.exists(), "image_describer_config.json must exist"
        
        with config_path.open('r') as f:
            config = json.load(f)
        
        # Verify required sections
        required_sections = [
            "default_model",
            "model_settings",
            "default_prompt_style",
            "prompt_variations",
            "metadata",
            "processing_options"
        ]
        for section in required_sections:
            assert section in config, f"Must have '{section}' section"
        
        # Verify default prompt style exists in variations
        default_style = config["default_prompt_style"]
        prompts = config["prompt_variations"]
        assert default_style in prompts, \
            f"Default style '{default_style}' must exist in prompt_variations"
        
        # Verify model settings have critical parameters
        model_settings = config["model_settings"]
        assert "temperature" in model_settings, "Must have temperature setting"
        assert "num_predict" in model_settings, "Must have num_predict setting"
        
        # Verify metadata section structure
        metadata = config["metadata"]
        assert "enabled" in metadata, "Metadata must have 'enabled' flag"
        assert "geocoding" in metadata, "Metadata must have 'geocoding' section"
    
    def test_video_frame_extractor_config_exists_and_valid(self):
        """Test video_frame_extractor_config.json exists and is valid JSON with required structure."""
        config_path = Path(__file__).parent.parent.parent / "scripts" / "video_frame_extractor_config.json"
        
        assert config_path.exists(), "video_frame_extractor_config.json must exist"
        
        with config_path.open('r') as f:
            config = json.load(f)
        
        # Verify required settings
        assert "extraction_mode" in config, "Must have extraction_mode"
        assert config["extraction_mode"] in ["time_interval", "scene_change"], \
            "extraction_mode must be valid value"
        assert "time_interval_seconds" in config, "Must have time_interval_seconds"
        assert "image_quality" in config, "Must have image_quality"
        
        # Verify frame naming structure
        assert "frame_naming" in config, "Must have frame_naming section"
        assert "format" in config["frame_naming"], "frame_naming must have format"
        
        # Verify timestamp preservation
        assert "timestamp_preservation" in config, "Must have timestamp_preservation"
        assert "enabled" in config["timestamp_preservation"], \
            "timestamp_preservation must have enabled flag"


class TestBasicConfigResolution:
    """Test basic configuration resolution paths."""
    
    def test_explicit_path_resolution(self):
        """Test that explicit --config path is resolved correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            
            config_file = tmp_path / "test_config.json"
            config_file.write_text('{"test": "explicit"}')
            
            path, source = resolve_config(
                "ignored_filename.json",
                explicit=str(config_file)
            )
            
            assert path == config_file, "Should resolve to explicit path"
            assert source == "explicit", "Source should be 'explicit'"
            assert path.exists(), "Resolved path should exist"
    
    def test_missing_config_returns_fallback(self):
        """Test that missing config returns fallback path gracefully."""
        path, source = resolve_config("nonexistent_config_12345.json")
        
        assert source == "missing_fallback", "Should return missing_fallback source"
        assert not path.exists(), "Fallback path should not exist"
        assert path.name == "nonexistent_config_12345.json", "Should preserve filename"
    
    def test_cwd_resolution(self):
        """Test that config in current working directory is found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            
            config_file = tmp_path / "test_cwd_config.json"
            config_file.write_text('{"test": "cwd"}')
            
            original_cwd = Path.cwd()
            try:
                os.chdir(tmp_path)
                
                path, source = resolve_config("test_cwd_config.json")
                
                assert path == config_file, "Should find config in cwd"
                assert source == "cwd", "Source should be 'cwd'"
                
            finally:
                os.chdir(original_cwd)


class TestConfigLoader:
    """Test JSON configuration loading."""
    
    def test_load_valid_json(self):
        """Test loading valid JSON configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            
            config_file = tmp_path / "valid.json"
            test_data = {
                "model": "test_model",
                "prompts": {"style1": "prompt text"}
            }
            config_file.write_text(json.dumps(test_data))
            
            config, path, source = load_json_config(
                "valid.json",
                explicit=str(config_file)
            )
            
            assert config == test_data, "Should load JSON correctly"
            assert path == config_file, "Should return correct path"
            assert source == "explicit", "Should return correct source"
    
    def test_load_invalid_json_returns_empty_dict(self):
        """Test that invalid JSON returns empty dict gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            
            config_file = tmp_path / "invalid.json"
            config_file.write_text('{invalid json}')
            
            config, path, source = load_json_config(
                "invalid.json",
                explicit=str(config_file)
            )
            
            assert config == {}, "Should return empty dict for invalid JSON"
            assert path == config_file, "Should still return path"
    
    def test_load_missing_config_returns_empty_dict(self):
        """Test that missing config returns empty dict gracefully."""
        config, path, source = load_json_config("missing_12345.json")
        
        assert config == {}, "Should return empty dict for missing file"
        assert source == "missing_fallback", "Should indicate missing"


class TestEnvironmentVariables:
    """Test basic environment variable configuration."""
    
    def test_config_dir_env_var(self):
        """Test IDT_CONFIG_DIR environment variable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            
            config_dir = tmp_path / "configs"
            config_dir.mkdir()
            
            config_file = config_dir / "test_config.json"
            config_file.write_text('{"test": "config_dir"}')
            
            # Save and set env var
            old_val = os.environ.get("IDT_CONFIG_DIR")
            try:
                os.environ["IDT_CONFIG_DIR"] = str(config_dir)
                
                path, source = resolve_config("test_config.json")
                
                assert path == config_file, "Should find config in IDT_CONFIG_DIR"
                assert source == "idt_config_dir", "Source should be idt_config_dir"
                
            finally:
                # Restore original value
                if old_val is None:
                    os.environ.pop("IDT_CONFIG_DIR", None)
                else:
                    os.environ["IDT_CONFIG_DIR"] = old_val
    
    def test_file_specific_env_var(self):
        """Test file-specific environment variable (e.g., IDT_WORKFLOW_CONFIG)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            
            config_file = tmp_path / "custom_workflow.json"
            config_file.write_text('{"workflow": {"custom": true}}')
            
            # Save and set env var
            old_val = os.environ.get("IDT_WORKFLOW_CONFIG")
            try:
                os.environ["IDT_WORKFLOW_CONFIG"] = str(config_file)
                
                path, source = resolve_config(
                    "workflow_config.json",
                    env_var_file="IDT_WORKFLOW_CONFIG"
                )
                
                assert path == config_file, "Should find config via env var"
                assert source == "idt_workflow_config", "Source should match env var"
                
            finally:
                # Restore original value
                if old_val is None:
                    os.environ.pop("IDT_WORKFLOW_CONFIG", None)
                else:
                    os.environ["IDT_WORKFLOW_CONFIG"] = old_val


class TestCustomPrompts:
    """Test custom prompt configuration loading."""
    
    def test_load_custom_prompts(self):
        """Test loading custom prompt configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            
            custom_prompts = {
                "default_model": "test_model",
                "default_prompt_style": "my_custom_style",
                "prompt_variations": {
                    "my_custom_style": "Custom prompt text",
                    "another_style": "Another prompt"
                },
                "model_settings": {
                    "temperature": 0.2,
                    "num_predict": 800
                }
            }
            
            custom_config = tmp_path / "my_prompts.json"
            custom_config.write_text(json.dumps(custom_prompts))
            
            config, path, source = load_json_config(
                "image_describer_config.json",
                explicit=str(custom_config)
            )
            
            assert config["default_prompt_style"] == "my_custom_style", \
                "Should load custom default style"
            assert "my_custom_style" in config["prompt_variations"], \
                "Should load custom prompt variations"
            assert config["model_settings"]["temperature"] == 0.2, \
                "Should load custom model settings"


class TestDocumentedBehavior:
    """Test that code matches documented behavior in CONFIGURATION_GUIDE.md."""
    
    def test_frozen_mode_detection_exists(self):
        """Test that frozen mode detection is implemented."""
        config_loader_path = Path(__file__).parent.parent.parent / "scripts" / "config_loader.py"
        
        with config_loader_path.open('r') as f:
            source = f.read()
        
        assert "getattr(sys, 'frozen', False)" in source, \
            "Must use documented frozen mode detection pattern"
    
    def test_search_order_documented(self):
        """Test that search order elements are present in config_loader.py."""
        config_loader_path = Path(__file__).parent.parent.parent / "scripts" / "config_loader.py"
        
        with config_loader_path.open('r') as f:
            source = f.read()
        
        # Verify key search order elements are documented in code
        assert "1. Explicit path" in source or "explicit" in source.lower(), \
            "Must document explicit path priority"
        assert "IDT_CONFIG_DIR" in source, \
            "Must support IDT_CONFIG_DIR"
        assert "sys.executable" in source, \
            "Must support frozen exe path resolution"
    
    def test_all_three_config_files_exist(self):
        """Test that all three documented config files exist."""
        scripts_dir = Path(__file__).parent.parent.parent / "scripts"
        
        config_files = [
            "workflow_config.json",
            "image_describer_config.json",
            "video_frame_extractor_config.json"
        ]
        
        for config_file in config_files:
            path = scripts_dir / config_file
            assert path.exists(), f"Documented config '{config_file}' must exist"
            
            # Verify it's valid JSON
            with path.open('r') as f:
                config = json.load(f)
                assert isinstance(config, dict), f"{config_file} must be a JSON object"


class TestConfigFlagSupport:
    """Test that scripts properly support --config command-line flag (Oct 31 fixes)."""
    
    def test_list_prompts_accepts_config_argument(self):
        """Test list_prompts.py accepts and uses --config argument."""
        # Import the module
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
        import list_prompts
        
        # Verify load_prompt_styles accepts config_file parameter
        import inspect
        sig = inspect.signature(list_prompts.load_prompt_styles)
        assert 'config_file' in sig.parameters, "load_prompt_styles must accept config_file parameter"
        
        # Verify it has a default value (None)
        param = sig.parameters['config_file']
        assert param.default is None, "config_file should default to None"
    
    def test_guided_workflow_accepts_config_argument(self):
        """Test guided_workflow.py accepts and uses --config argument."""
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
        import guided_workflow
        
        # Verify guided_workflow function accepts custom_config_path
        import inspect
        sig = inspect.signature(guided_workflow.guided_workflow)
        assert 'custom_config_path' in sig.parameters, "guided_workflow must accept custom_config_path parameter"
        
        # Verify get_available_prompt_styles accepts custom_config_path
        sig2 = inspect.signature(guided_workflow.get_available_prompt_styles)
        assert 'custom_config_path' in sig2.parameters, "get_available_prompt_styles must accept custom_config_path"
    
    def test_workflow_orchestrator_stores_config_file(self):
        """Test WorkflowOrchestrator stores user's config file for subprocess passing."""
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
        import workflow
        
        # Create orchestrator with custom config
        orchestrator = workflow.WorkflowOrchestrator(
            config_file="test_config.json",
            base_output_dir=Path(tempfile.gettempdir())
        )
        
        # Verify it stores the config_file
        assert hasattr(orchestrator, 'config_file'), "Orchestrator must store config_file"
        assert orchestrator.config_file == "test_config.json", "Must store exact config file path"
    
    def test_list_prompts_uses_config_loader(self):
        """Test list_prompts.py uses config_loader instead of hardcoded paths."""
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
        import list_prompts
        
        # Read the source code to verify config_loader is imported
        source_file = Path(__file__).parent.parent.parent / "scripts" / "list_prompts.py"
        with source_file.open('r') as f:
            source = f.read()
        
        # Verify config_loader is imported
        assert 'from config_loader import load_json_config' in source, \
            "list_prompts must import load_json_config from config_loader"
        
        # Verify old find_config_file function is gone
        assert 'def find_config_file(' not in source, \
            "Old hardcoded find_config_file() should be removed"


if __name__ == "__main__":
    print("Run these tests with: python run_unit_tests.py pytest_tests/unit/test_configuration_system.py")
    print("For comprehensive test coverage, see GitHub Issue #62")
