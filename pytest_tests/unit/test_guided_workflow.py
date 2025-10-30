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
        
        # Mock all the interactive prompts
        with patch('guided_workflow.get_choice') as mock_choice, \
             patch('guided_workflow.get_input') as mock_input, \
             patch('guided_workflow.validate_directory') as mock_validate_dir, \
             patch('guided_workflow.create_view_results_bat'), \
             patch('guided_workflow.workflow_main') as mock_workflow:
            
            # Setup mock responses
            mock_choice.side_effect = [
                'ollama',  # Provider
                'moondream:latest',  # Model
                'No (recommended)',  # Metadata
                'Run this command now',  # Action
                'Use default (Descriptions)'  # Output dir
            ]
            mock_input.side_effect = [
                '/test/images',  # Image directory
                '',  # Workflow name (empty = skip)
                ''   # Prompt style (empty = skip)
            ]
            mock_validate_dir.return_value = (True, None)
            
            # Run guideme
            guided_workflow()
            
            # Check that workflow was called with correct args
            mock_workflow.assert_called_once()
            args = mock_workflow.call_args[0][0]
            
            # Should have --no-metadata, should NOT have --geocode or --no-geocode
            assert '--no-metadata' in args
            assert '--geocode' not in args
            assert '--no-geocode' not in args
    
    def test_metadata_enabled_geocoding_enabled(self):
        """Test command with metadata and geocoding both enabled (default behavior)"""
        from guided_workflow import guided_workflow
        
        with patch('guided_workflow.get_choice') as mock_choice, \
             patch('guided_workflow.get_input') as mock_input, \
             patch('guided_workflow.check_directory') as mock_check_dir, \
             patch('guided_workflow.create_view_results_bat'), \
             patch('guided_workflow.workflow_main') as mock_workflow:
            
            mock_choice.side_effect = [
                'ollama',
                'moondream:latest',
                'Yes (recommended)',  # Enable metadata
                'Yes',  # Enable geocoding
                'Run this command now',
                'Use default (Descriptions)'
            ]
            mock_input.side_effect = [
                '/test/images',
                '',  # Workflow name
                '',  # Prompt style
                ''   # Geocode cache (use default)
            ]
            mock_check_dir.return_value = (True, None)
            
            guided_workflow()
            
            args = mock_workflow.call_args[0][0]
            
            # Should NOT have --no-metadata, should NOT have --no-geocode (both default ON)
            # Should NOT have --geocode (old flag that no longer exists)
            assert '--no-metadata' not in args
            assert '--no-geocode' not in args
            assert '--geocode' not in args
            assert '--geocode-cache' not in args  # Using default, shouldn't be specified
    
    def test_metadata_enabled_geocoding_disabled(self):
        """Test command with metadata enabled but geocoding explicitly disabled"""
        from guided_workflow import guided_workflow
        
        with patch('guided_workflow.get_choice') as mock_choice, \
             patch('guided_workflow.get_input') as mock_input, \
             patch('guided_workflow.check_directory') as mock_check_dir, \
             patch('guided_workflow.create_view_results_bat'), \
             patch('guided_workflow.workflow_main') as mock_workflow:
            
            mock_choice.side_effect = [
                'ollama',
                'moondream:latest',
                'Yes (recommended)',  # Enable metadata
                'No (skip geocoding)',  # Disable geocoding
                'Run this command now',
                'Use default (Descriptions)'
            ]
            mock_input.side_effect = [
                '/test/images',
                '',  # Workflow name
                ''   # Prompt style
            ]
            mock_check_dir.return_value = (True, None)
            
            guided_workflow()
            
            args = mock_workflow.call_args[0][0]
            
            # Should have --no-geocode to explicitly disable it
            assert '--no-geocode' in args
            assert '--no-metadata' not in args
            assert '--geocode' not in args
    
    def test_custom_geocode_cache(self):
        """Test that custom geocode cache location is properly added"""
        from guided_workflow import guided_workflow
        
        with patch('guided_workflow.get_choice') as mock_choice, \
             patch('guided_workflow.get_input') as mock_input, \
             patch('guided_workflow.check_directory') as mock_check_dir, \
             patch('guided_workflow.create_view_results_bat'), \
             patch('guided_workflow.workflow_main') as mock_workflow:
            
            mock_choice.side_effect = [
                'ollama',
                'moondream:latest',
                'Yes (recommended)',
                'Yes',
                'Run this command now',
                'Use default (Descriptions)'
            ]
            mock_input.side_effect = [
                '/test/images',
                '',
                '',
                'custom_cache.json'  # Custom cache file
            ]
            mock_check_dir.return_value = (True, None)
            
            guided_workflow()
            
            args = mock_workflow.call_args[0][0]
            
            # Should have --geocode-cache with custom value
            assert '--geocode-cache' in args
            cache_idx = args.index('--geocode-cache')
            assert args[cache_idx + 1] == 'custom_cache.json'
    
    def test_default_geocode_cache_not_added(self):
        """Test that default geocode cache is NOT added to command (workflow.py default)"""
        from guided_workflow import guided_workflow
        
        with patch('guided_workflow.get_choice') as mock_choice, \
             patch('guided_workflow.get_input') as mock_input, \
             patch('guided_workflow.check_directory') as mock_check_dir, \
             patch('guided_workflow.create_view_results_bat'), \
             patch('guided_workflow.workflow_main') as mock_workflow:
            
            mock_choice.side_effect = [
                'ollama',
                'moondream:latest',
                'Yes (recommended)',
                'Yes',
                'Run this command now',
                'Use default (Descriptions)'
            ]
            mock_input.side_effect = [
                '/test/images',
                '',
                '',
                ''  # Empty = use default geocode_cache.json
            ]
            mock_check_dir.return_value = (True, None)
            
            guided_workflow()
            
            args = mock_workflow.call_args[0][0]
            
            # Should NOT have --geocode-cache when using default
            assert '--geocode-cache' not in args
    
    def test_extra_workflow_args_passthrough(self):
        """Test that extra workflow args like --timeout are passed through"""
        from guided_workflow import guided_workflow
        
        with patch('guided_workflow.get_choice') as mock_choice, \
             patch('guided_workflow.get_input') as mock_input, \
             patch('guided_workflow.check_directory') as mock_check_dir, \
             patch('guided_workflow.create_view_results_bat'), \
             patch('guided_workflow.workflow_main') as mock_workflow, \
             patch.object(sys, 'argv', ['guideme', '--timeout', '300']):
            
            mock_choice.side_effect = [
                'ollama',
                'moondream:latest',
                'No (recommended)',
                'Run this command now',
                'Use default (Descriptions)'
            ]
            mock_input.side_effect = [
                '/test/images',
                '',
                ''
            ]
            mock_check_dir.return_value = (True, None)
            
            guided_workflow()
            
            args = mock_workflow.call_args[0][0]
            
            # Should have --timeout 300 passed through
            assert '--timeout' in args
            timeout_idx = args.index('--timeout')
            assert args[timeout_idx + 1] == '300'
    
    def test_no_geocode_flag_passthrough(self):
        """Test that --no-geocode can be passed through from command line"""
        from guided_workflow import guided_workflow
        
        with patch('guided_workflow.get_choice') as mock_choice, \
             patch('guided_workflow.get_input') as mock_input, \
             patch('guided_workflow.check_directory') as mock_check_dir, \
             patch('guided_workflow.create_view_results_bat'), \
             patch('guided_workflow.workflow_main') as mock_workflow, \
             patch.object(sys, 'argv', ['guideme', '--no-geocode']):
            
            mock_choice.side_effect = [
                'ollama',
                'moondream:latest',
                'Yes (recommended)',  # Enable metadata
                'No (skip geocoding)',  # Disable geocoding (should be redundant with --no-geocode)
                'Run this command now',
                'Use default (Descriptions)'
            ]
            mock_input.side_effect = [
                '/test/images',
                '',
                ''
            ]
            mock_check_dir.return_value = (True, None)
            
            guided_workflow()
            
            args = mock_workflow.call_args[0][0]
            
            # Should have --no-geocode
            assert '--no-geocode' in args
            # Should NOT have old --geocode flag
            assert '--geocode' not in args
    
    def test_old_geocode_flag_not_accepted(self):
        """Test that the old --geocode flag is NOT in the allowed passthrough list"""
        from guided_workflow import guided_workflow
        
        with patch('guided_workflow.get_choice') as mock_choice, \
             patch('guided_workflow.get_input') as mock_input, \
             patch('guided_workflow.check_directory') as mock_check_dir, \
             patch('guided_workflow.create_view_results_bat'), \
             patch('guided_workflow.workflow_main') as mock_workflow, \
             patch.object(sys, 'argv', ['guideme', '--geocode']):  # Old flag
            
            mock_choice.side_effect = [
                'ollama',
                'moondream:latest',
                'Yes (recommended)',
                'Yes',
                'Run this command now',
                'Use default (Descriptions)'
            ]
            mock_input.side_effect = [
                '/test/images',
                '',
                '',
                ''
            ]
            mock_check_dir.return_value = (True, None)
            
            guided_workflow()
            
            args = mock_workflow.call_args[0][0]
            
            # Old --geocode flag should NOT be passed through
            assert '--geocode' not in args
    
    def test_all_workflow_options(self):
        """Test command with all options specified"""
        from guided_workflow import guided_workflow
        
        with patch('guided_workflow.get_choice') as mock_choice, \
             patch('guided_workflow.get_input') as mock_input, \
             patch('guided_workflow.check_directory') as mock_check_dir, \
             patch('guided_workflow.create_view_results_bat'), \
             patch('guided_workflow.workflow_main') as mock_workflow:
            
            mock_choice.side_effect = [
                'ollama',
                'moondream:latest',
                'Yes (recommended)',
                'Yes',
                'Run this command now',
                'Use default (Descriptions)'
            ]
            mock_input.side_effect = [
                '/test/images',
                'MyWorkflow',  # Custom workflow name
                'colorful',  # Custom prompt style
                'my_cache.json'  # Custom cache
            ]
            mock_check_dir.return_value = (True, None)
            
            guided_workflow()
            
            args = mock_workflow.call_args[0][0]
            
            # Check all expected args are present
            assert args[0] == '/test/images'  # Input dir
            assert '--provider' in args and 'ollama' in args
            assert '--model' in args and 'moondream:latest' in args
            assert '--name' in args and 'MyWorkflow' in args
            assert '--prompt-style' in args and 'colorful' in args
            assert '--geocode-cache' in args and 'my_cache.json' in args
            assert '--output-dir' in args and 'Descriptions' in args
            
            # Should NOT have flags for defaults
            assert '--no-metadata' not in args
            assert '--no-geocode' not in args
            assert '--geocode' not in args


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
        
        with patch('guided_workflow.get_choice') as mock_choice, \
             patch('guided_workflow.get_input') as mock_input, \
             patch('guided_workflow.check_directory') as mock_check_dir, \
             patch('guided_workflow.create_view_results_bat'), \
             patch('guided_workflow.workflow_main') as mock_workflow:
            
            mock_choice.side_effect = [
                'ollama',
                'moondream:latest',
                'Yes (recommended)',
                'Yes',
                'Run this command now',
                'Use default (Descriptions)'
            ]
            mock_input.side_effect = [
                '/test/images',
                '',
                '',
                '   '  # Whitespace only - should be treated as empty
            ]
            mock_check_dir.return_value = (True, None)
            
            guided_workflow()
            
            args = mock_workflow.call_args[0][0]
            
            # Should NOT add --geocode-cache with empty/whitespace value
            assert '--geocode-cache' not in args
    
    def test_geocode_cache_without_geocoding_enabled(self):
        """Test that geocode cache is not added if geocoding is disabled"""
        from guided_workflow import guided_workflow
        
        with patch('guided_workflow.get_choice') as mock_choice, \
             patch('guided_workflow.get_input') as mock_input, \
             patch('guided_workflow.check_directory') as mock_check_dir, \
             patch('guided_workflow.create_view_results_bat'), \
             patch('guided_workflow.workflow_main') as mock_workflow:
            
            mock_choice.side_effect = [
                'ollama',
                'moondream:latest',
                'Yes (recommended)',  # Metadata enabled
                'No (skip geocoding)',  # Geocoding disabled
                'Run this command now',
                'Use default (Descriptions)'
            ]
            mock_input.side_effect = [
                '/test/images',
                '',
                ''
            ]
            mock_check_dir.return_value = (True, None)
            
            guided_workflow()
            
            args = mock_workflow.call_args[0][0]
            
            # Should have --no-geocode, should NOT have --geocode-cache
            assert '--no-geocode' in args
            assert '--geocode-cache' not in args


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
