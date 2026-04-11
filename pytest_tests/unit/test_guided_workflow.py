"""
Tests for guided_workflow.py command generation and CLI integration

These tests validate that guideme generates correct workflow commands
with proper flags based on user choices.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add scripts directory to path
scripts_path = Path(__file__).parent.parent.parent / 'scripts'
sys.path.insert(0, str(scripts_path))


class TestGuidedWorkflowCommandGeneration:
    """Test that guideme generates correct workflow commands for various scenarios"""
    
    def test_basic_command_no_metadata_no_geocoding(self):
        """Test command generation with metadata and geocoding disabled"""
        from guided_workflow import guided_workflow

        captured_args = []
        def capture_workflow_args():
            captured_args[:] = list(sys.argv[1:])  # sys.argv[0] is 'workflow.py'

        # Mock all the interactive prompts
        with patch('guided_workflow.get_choice') as mock_choice, \
             patch('guided_workflow.get_input') as mock_input, \
             patch('guided_workflow.validate_directory') as mock_validate_dir, \
             patch('guided_workflow.create_view_results_bat'), \
             patch('guided_workflow.check_ollama_models', return_value=['moondream:latest']), \
             patch('guided_workflow.get_available_prompt_styles', return_value=(['descriptions', 'general'], 'descriptions')), \
             patch('workflow.main') as mock_workflow:

            mock_workflow.side_effect = capture_workflow_args

            # Provider, Model, Prompt style (skip), Metadata (No), Action, Output dir
            mock_choice.side_effect = [
                'ollama',
                'moondream:latest',
                'Skip (use default)',  # Prompt style
                'No',                  # Metadata disabled
                'Run this command now',
                'Use default (Descriptions)'
            ]
            mock_input.side_effect = [
                '/test/images',  # Image directory
                '',              # Workflow name (empty = skip)
            ]
            mock_validate_dir.return_value = (True, None)

            guided_workflow()

            # Check that workflow was called with correct args
            mock_workflow.assert_called_once()

            # Should have --no-metadata, should NOT have --geocode or --no-geocode
            assert '--no-metadata' in captured_args
            assert '--geocode' not in captured_args
            assert '--no-geocode' not in captured_args
    
    def test_metadata_enabled_geocoding_enabled(self):
        """Test command with metadata and geocoding both enabled (default behavior)"""
        from guided_workflow import guided_workflow

        captured_args = []
        def capture_workflow_args():
            captured_args[:] = list(sys.argv[1:])

        with patch('guided_workflow.get_choice') as mock_choice, \
             patch('guided_workflow.get_input') as mock_input, \
             patch('guided_workflow.validate_directory') as mock_check_dir, \
             patch('guided_workflow.create_view_results_bat'), \
             patch('guided_workflow.check_ollama_models', return_value=['moondream:latest']), \
             patch('guided_workflow.get_available_prompt_styles', return_value=(['descriptions', 'general'], 'descriptions')), \
             patch('workflow.main') as mock_workflow:

            mock_workflow.side_effect = capture_workflow_args

            # Provider, Model, Prompt style (skip), Metadata (Yes), Geocoding (Yes), Action, Output dir
            mock_choice.side_effect = [
                'ollama',
                'moondream:latest',
                'Skip (use default)',   # Prompt style
                'Yes (recommended)',    # Enable metadata
                'Yes',                  # Enable geocoding
                'Run this command now',
                'Use default (Descriptions)'
            ]
            mock_input.side_effect = [
                '/test/images',
                '',   # Workflow name
                '',   # Geocode cache (empty = use default, which is omitted)
            ]
            mock_check_dir.return_value = (True, None)

            guided_workflow()

            # Should NOT have --no-metadata, should NOT have --no-geocode (both default ON)
            # Should NOT have --geocode (old flag that no longer exists)
            assert '--no-metadata' not in captured_args
            assert '--no-geocode' not in captured_args
            assert '--geocode' not in captured_args
            assert '--geocode-cache' not in captured_args  # Using default, shouldn't be specified
    
    def test_metadata_enabled_geocoding_disabled(self):
        """Test command with metadata enabled but geocoding explicitly disabled"""
        from guided_workflow import guided_workflow

        captured_args = []
        def capture_workflow_args():
            captured_args[:] = list(sys.argv[1:])

        with patch('guided_workflow.get_choice') as mock_choice, \
             patch('guided_workflow.get_input') as mock_input, \
             patch('guided_workflow.validate_directory') as mock_check_dir, \
             patch('guided_workflow.create_view_results_bat'), \
             patch('guided_workflow.check_ollama_models', return_value=['moondream:latest']), \
             patch('guided_workflow.get_available_prompt_styles', return_value=(['descriptions', 'general'], 'descriptions')), \
             patch('workflow.main') as mock_workflow:

            mock_workflow.side_effect = capture_workflow_args

            # Provider, Model, Prompt style (skip), Metadata (Yes), Geocoding (No), Action, Output dir
            mock_choice.side_effect = [
                'ollama',
                'moondream:latest',
                'Skip (use default)',   # Prompt style
                'Yes (recommended)',    # Enable metadata
                'No (skip geocoding)',  # Disable geocoding
                'Run this command now',
                'Use default (Descriptions)'
            ]
            mock_input.side_effect = [
                '/test/images',
                '',  # Workflow name
            ]
            mock_check_dir.return_value = (True, None)

            guided_workflow()

            # Should have --no-geocode to explicitly disable it
            assert '--no-geocode' in captured_args
            assert '--no-metadata' not in captured_args
            assert '--geocode' not in captured_args
    
    def test_custom_geocode_cache(self):
        """Test that custom geocode cache location is properly added"""
        from guided_workflow import guided_workflow

        captured_args = []
        def capture_workflow_args():
            captured_args[:] = list(sys.argv[1:])

        with patch('guided_workflow.get_choice') as mock_choice, \
             patch('guided_workflow.get_input') as mock_input, \
             patch('guided_workflow.validate_directory') as mock_check_dir, \
             patch('guided_workflow.create_view_results_bat'), \
             patch('guided_workflow.check_ollama_models', return_value=['moondream:latest']), \
             patch('guided_workflow.get_available_prompt_styles', return_value=(['descriptions', 'general'], 'descriptions')), \
             patch('workflow.main') as mock_workflow:

            mock_workflow.side_effect = capture_workflow_args

            mock_choice.side_effect = [
                'ollama',
                'moondream:latest',
                'Skip (use default)',   # Prompt style
                'Yes (recommended)',    # Metadata
                'Yes',                  # Geocoding
                'Run this command now',
                'Use default (Descriptions)'
            ]
            mock_input.side_effect = [
                '/test/images',
                '',                  # Workflow name
                'custom_cache.json'  # Custom cache file
            ]
            mock_check_dir.return_value = (True, None)

            guided_workflow()

            # Should have --geocode-cache with custom value
            assert '--geocode-cache' in captured_args
            cache_idx = captured_args.index('--geocode-cache')
            assert captured_args[cache_idx + 1] == 'custom_cache.json'
    
    def test_default_geocode_cache_not_added(self):
        """Test that default geocode cache is NOT added to command (workflow.py default)"""
        from guided_workflow import guided_workflow

        captured_args = []
        def capture_workflow_args():
            captured_args[:] = list(sys.argv[1:])

        with patch('guided_workflow.get_choice') as mock_choice, \
             patch('guided_workflow.get_input') as mock_input, \
             patch('guided_workflow.validate_directory') as mock_check_dir, \
             patch('guided_workflow.create_view_results_bat'), \
             patch('guided_workflow.check_ollama_models', return_value=['moondream:latest']), \
             patch('guided_workflow.get_available_prompt_styles', return_value=(['descriptions', 'general'], 'descriptions')), \
             patch('workflow.main') as mock_workflow:

            mock_workflow.side_effect = capture_workflow_args

            mock_choice.side_effect = [
                'ollama',
                'moondream:latest',
                'Skip (use default)',  # Prompt style
                'Yes (recommended)',   # Metadata
                'Yes',                 # Geocoding
                'Run this command now',
                'Use default (Descriptions)'
            ]
            mock_input.side_effect = [
                '/test/images',
                '',  # Workflow name
                '',  # Geocode cache empty = use default (not added)
            ]
            mock_check_dir.return_value = (True, None)

            guided_workflow()

            # Should NOT have --geocode-cache when using default
            assert '--geocode-cache' not in captured_args
    
    def test_extra_workflow_args_passthrough(self):
        """Test that extra workflow args like --timeout are passed through"""
        from guided_workflow import guided_workflow

        captured_args = []
        def capture_workflow_args():
            captured_args[:] = list(sys.argv[1:])

        with patch('guided_workflow.get_choice') as mock_choice, \
             patch('guided_workflow.get_input') as mock_input, \
             patch('guided_workflow.validate_directory') as mock_check_dir, \
             patch('guided_workflow.create_view_results_bat'), \
             patch('guided_workflow.check_ollama_models', return_value=['moondream:latest']), \
             patch('guided_workflow.get_available_prompt_styles', return_value=(['descriptions', 'general'], 'descriptions')), \
             patch('workflow.main') as mock_workflow, \
             patch.object(sys, 'argv', ['guideme', '--timeout', '300']):

            mock_workflow.side_effect = capture_workflow_args

            mock_choice.side_effect = [
                'ollama',
                'moondream:latest',
                'Skip (use default)',  # Prompt style
                'No',                  # Metadata disabled
                'Run this command now',
                'Use default (Descriptions)'
            ]
            mock_input.side_effect = [
                '/test/images',
                '',   # Workflow name
            ]
            mock_check_dir.return_value = (True, None)

            guided_workflow()

            # Should have --timeout 300 passed through
            assert '--timeout' in captured_args
            timeout_idx = captured_args.index('--timeout')
            assert captured_args[timeout_idx + 1] == '300'
    
    def test_no_geocode_flag_passthrough(self):
        """Test that --no-geocode can be passed through from command line"""
        from guided_workflow import guided_workflow

        captured_args = []
        def capture_workflow_args():
            captured_args[:] = list(sys.argv[1:])

        with patch('guided_workflow.get_choice') as mock_choice, \
             patch('guided_workflow.get_input') as mock_input, \
             patch('guided_workflow.validate_directory') as mock_check_dir, \
             patch('guided_workflow.create_view_results_bat'), \
             patch('guided_workflow.check_ollama_models', return_value=['moondream:latest']), \
             patch('guided_workflow.get_available_prompt_styles', return_value=(['descriptions', 'general'], 'descriptions')), \
             patch('workflow.main') as mock_workflow, \
             patch.object(sys, 'argv', ['guideme', '--no-geocode']):

            mock_workflow.side_effect = capture_workflow_args

            mock_choice.side_effect = [
                'ollama',
                'moondream:latest',
                'Skip (use default)',   # Prompt style
                'Yes (recommended)',    # Enable metadata
                'No (skip geocoding)',  # Disable geocoding (redundant with --no-geocode)
                'Run this command now',
                'Use default (Descriptions)'
            ]
            mock_input.side_effect = [
                '/test/images',
                '',   # Workflow name
            ]
            mock_check_dir.return_value = (True, None)

            guided_workflow()

            # Should have --no-geocode
            assert '--no-geocode' in captured_args
            # Should NOT have old --geocode flag
            assert '--geocode' not in captured_args
    
    def test_old_geocode_flag_not_accepted(self):
        """Test that the old --geocode flag is NOT in the allowed passthrough list"""
        from guided_workflow import guided_workflow

        captured_args = []
        def capture_workflow_args():
            captured_args[:] = list(sys.argv[1:])

        with patch('guided_workflow.get_choice') as mock_choice, \
             patch('guided_workflow.get_input') as mock_input, \
             patch('guided_workflow.validate_directory') as mock_check_dir, \
             patch('guided_workflow.create_view_results_bat'), \
             patch('guided_workflow.check_ollama_models', return_value=['moondream:latest']), \
             patch('guided_workflow.get_available_prompt_styles', return_value=(['descriptions', 'general'], 'descriptions')), \
             patch('workflow.main') as mock_workflow, \
             patch.object(sys, 'argv', ['guideme', '--geocode']):  # Old flag

            mock_workflow.side_effect = capture_workflow_args

            mock_choice.side_effect = [
                'ollama',
                'moondream:latest',
                'Skip (use default)',  # Prompt style
                'Yes (recommended)',   # Metadata
                'Yes',                 # Geocoding
                'Run this command now',
                'Use default (Descriptions)'
            ]
            mock_input.side_effect = [
                '/test/images',
                '',   # Workflow name
                '',   # Geocode cache
            ]
            mock_check_dir.return_value = (True, None)

            guided_workflow()

            # Old --geocode flag should NOT be passed through
            assert '--geocode' not in captured_args
    
    def test_all_workflow_options(self):
        """Test command with all options specified"""
        from guided_workflow import guided_workflow

        captured_args = []
        def capture_workflow_args():
            captured_args[:] = list(sys.argv[1:])

        with patch('guided_workflow.get_choice') as mock_choice, \
             patch('guided_workflow.get_input') as mock_input, \
             patch('guided_workflow.validate_directory') as mock_check_dir, \
             patch('guided_workflow.create_view_results_bat'), \
             patch('guided_workflow.check_ollama_models', return_value=['moondream:latest']), \
             patch('guided_workflow.get_available_prompt_styles', return_value=(['descriptions', 'colorful', 'general'], 'descriptions')), \
             patch('workflow.main') as mock_workflow:

            mock_workflow.side_effect = capture_workflow_args

            # Provider, Model, Prompt style (colorful), Metadata (Yes), Geocoding (Yes), Action, Output dir
            mock_choice.side_effect = [
                'ollama',
                'moondream:latest',
                'colorful',           # Prompt style
                'Yes (recommended)',  # Metadata
                'Yes',                # Geocoding
                'Run this command now',
                'Use default (Descriptions)'
            ]
            mock_input.side_effect = [
                '/test/images',
                'MyWorkflow',    # Custom workflow name
                'my_cache.json'  # Custom geocode cache
            ]
            mock_check_dir.return_value = (True, None)

            guided_workflow()

            # Check all expected args are present
            assert captured_args[0] == '/test/images'  # Input dir is first arg
            assert '--provider' in captured_args and 'ollama' in captured_args
            assert '--model' in captured_args and 'moondream:latest' in captured_args
            assert '--name' in captured_args and 'MyWorkflow' in captured_args
            assert '--prompt-style' in captured_args and 'colorful' in captured_args
            assert '--geocode-cache' in captured_args and 'my_cache.json' in captured_args
            assert '--output-dir' in captured_args and 'Descriptions' in captured_args

            # Should NOT have flags for defaults
            assert '--no-metadata' not in captured_args
            assert '--no-geocode' not in captured_args
            assert '--geocode' not in captured_args


class TestGuidedWorkflowFlagCompatibility:
    """Test compatibility between guideme flags and workflow.py argparse"""
    
    def test_metadata_flags_compatibility(self):
        """Ensure metadata flags match between guideme and workflow.py"""
        # These should be the valid flags that both support
        valid_metadata_flags = ['--metadata', '--no-metadata']
        
        # The old --geocode flag should NOT be valid
        invalid_flags = ['--geocode']
        
        # Test that guided_workflow only uses valid flags
        from guided_workflow import guided_workflow
        import guided_workflow as gw_module
        
        # Check the source code for flag references
        import inspect
        source = inspect.getsource(gw_module)
        
        # Should NOT contain references to old --geocode flag in command building
        # (it might appear in comments or old code paths, but not in active use)
        assert source.count("extra_workflow_args.append(\"--geocode\")") == 0, \
            "Found old --geocode flag being added to commands"
    
    def test_geocoding_flags_compatibility(self):
        """Ensure geocoding flags match between guideme and workflow.py"""
        valid_geocoding_flags = ['--no-geocode', '--geocode-cache']
        
        from guided_workflow import guided_workflow
        import guided_workflow as gw_module
        import inspect
        
        source = inspect.getsource(gw_module)
        
        # Check that --no-geocode is used, not --geocode
        assert "'--no-geocode'" in source or '"--no-geocode"' in source, \
            "--no-geocode flag not found in guided_workflow"
        
        # The passthrough list should include --no-geocode
        assert "--no-geocode" in source and "--geocode-cache" in source, \
            "Geocoding flags not properly configured in passthrough list"


class TestGuidedWorkflowEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_empty_geocode_cache_not_added(self):
        """Test that empty geocode cache string doesn't add flag"""
        from guided_workflow import guided_workflow

        captured_args = []
        def capture_workflow_args():
            captured_args[:] = list(sys.argv[1:])

        with patch('guided_workflow.get_choice') as mock_choice, \
             patch('guided_workflow.get_input') as mock_input, \
             patch('guided_workflow.validate_directory') as mock_check_dir, \
             patch('guided_workflow.create_view_results_bat'), \
             patch('guided_workflow.check_ollama_models', return_value=['moondream:latest']), \
             patch('guided_workflow.get_available_prompt_styles', return_value=(['descriptions', 'general'], 'descriptions')), \
             patch('workflow.main') as mock_workflow:

            mock_workflow.side_effect = capture_workflow_args

            mock_choice.side_effect = [
                'ollama',
                'moondream:latest',
                'Skip (use default)',  # Prompt style
                'Yes (recommended)',   # Metadata
                'Yes',                 # Geocoding
                'Run this command now',
                'Use default (Descriptions)'
            ]
            mock_input.side_effect = [
                '/test/images',
                '',    # Workflow name
                '   '  # Whitespace only - should be treated as empty
            ]
            mock_check_dir.return_value = (True, None)

            guided_workflow()

            # Should NOT add --geocode-cache with empty/whitespace value
            assert '--geocode-cache' not in captured_args
    
    def test_geocode_cache_without_geocoding_enabled(self):
        """Test that geocode cache is not added if geocoding is disabled"""
        from guided_workflow import guided_workflow

        captured_args = []
        def capture_workflow_args():
            captured_args[:] = list(sys.argv[1:])

        with patch('guided_workflow.get_choice') as mock_choice, \
             patch('guided_workflow.get_input') as mock_input, \
             patch('guided_workflow.validate_directory') as mock_check_dir, \
             patch('guided_workflow.create_view_results_bat'), \
             patch('guided_workflow.check_ollama_models', return_value=['moondream:latest']), \
             patch('guided_workflow.get_available_prompt_styles', return_value=(['descriptions', 'general'], 'descriptions')), \
             patch('workflow.main') as mock_workflow:

            mock_workflow.side_effect = capture_workflow_args

            mock_choice.side_effect = [
                'ollama',
                'moondream:latest',
                'Skip (use default)',   # Prompt style
                'Yes (recommended)',    # Metadata enabled
                'No (skip geocoding)',  # Geocoding disabled
                'Run this command now',
                'Use default (Descriptions)'
            ]
            mock_input.side_effect = [
                '/test/images',
                '',   # Workflow name
            ]
            mock_check_dir.return_value = (True, None)

            guided_workflow()

            # Should have --no-geocode, should NOT have --geocode-cache
            assert '--no-geocode' in captured_args
            assert '--geocode-cache' not in captured_args


class TestMLXProviderPlatformFiltering:
    """Test that MLX provider is only offered on Apple Silicon Macs"""

    def test_mlx_not_in_providers_on_linux(self):
        """MLX should not appear in the providers list on Linux"""
        from guided_workflow import get_available_providers
        with patch('guided_workflow.sys') as mock_sys, \
             patch('guided_workflow.platform') as mock_platform:
            mock_sys.platform = 'linux'
            mock_platform.machine.return_value = 'x86_64'
            assert 'mlx' not in get_available_providers()

    def test_mlx_not_in_providers_on_windows(self):
        """MLX should not appear in the providers list on Windows"""
        from guided_workflow import get_available_providers
        with patch('guided_workflow.sys') as mock_sys, \
             patch('guided_workflow.platform') as mock_platform:
            mock_sys.platform = 'win32'
            mock_platform.machine.return_value = 'AMD64'
            assert 'mlx' not in get_available_providers()

    def test_mlx_not_in_providers_on_intel_mac(self):
        """MLX should not appear in the providers list on Intel Macs"""
        from guided_workflow import get_available_providers
        with patch('guided_workflow.sys') as mock_sys, \
             patch('guided_workflow.platform') as mock_platform:
            mock_sys.platform = 'darwin'
            mock_platform.machine.return_value = 'x86_64'
            assert 'mlx' not in get_available_providers()

    def test_mlx_in_providers_on_apple_silicon(self):
        """MLX should appear in the providers list on Apple Silicon Macs"""
        from guided_workflow import get_available_providers
        with patch('guided_workflow.sys') as mock_sys, \
             patch('guided_workflow.platform') as mock_platform:
            mock_sys.platform = 'darwin'
            mock_platform.machine.return_value = 'arm64'
            assert 'mlx' in get_available_providers()


class TestMLXProviderAvailability:
    """Test MLXProvider.is_available() correctly requires Apple Silicon"""

    def test_mlx_unavailable_on_linux(self):
        """MLXProvider.is_available() should return False on Linux"""
        import platform as _platform
        with patch.object(_platform, 'system', return_value='Linux'), \
             patch.object(_platform, 'machine', return_value='x86_64'):
            # Import here so the patch applies
            from imagedescriber.ai_providers import MLXProvider
            provider = MLXProvider()
            assert provider.is_available() is False

    def test_mlx_unavailable_on_windows(self):
        """MLXProvider.is_available() should return False on Windows"""
        import platform as _platform
        with patch.object(_platform, 'system', return_value='Windows'), \
             patch.object(_platform, 'machine', return_value='AMD64'):
            from imagedescriber.ai_providers import MLXProvider
            provider = MLXProvider()
            assert provider.is_available() is False

    def test_mlx_unavailable_on_intel_mac(self):
        """MLXProvider.is_available() should return False on Intel Mac"""
        import platform as _platform
        with patch.object(_platform, 'system', return_value='Darwin'), \
             patch.object(_platform, 'machine', return_value='x86_64'):
            from imagedescriber.ai_providers import MLXProvider
            provider = MLXProvider()
            assert provider.is_available() is False

    def test_mlx_available_on_apple_silicon_with_mlx_vlm(self):
        """MLXProvider.is_available() should return True on Apple Silicon with mlx-vlm installed"""
        import platform as _platform
        import imagedescriber.ai_providers as ai_providers_mod
        with patch.object(_platform, 'system', return_value='Darwin'), \
             patch.object(_platform, 'machine', return_value='arm64'), \
             patch.object(ai_providers_mod, 'HAS_MLX_VLM', True):
            from imagedescriber.ai_providers import MLXProvider
            provider = MLXProvider()
            assert provider.is_available() is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
