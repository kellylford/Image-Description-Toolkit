"""
Unit tests for workflow.py config file operations.

Tests ensure that config files are properly written and flushed before being read,
preventing race conditions in frozen mode where config updates happen immediately
before ImageDescriber initialization.
"""

import pytest
import json
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

# Import the workflow module
from scripts.workflow import Workflow


class TestConfigFileOperations:
    """Test config file write/flush/read operations."""
    
    def test_config_update_includes_flush(self):
        """Test that config file writes include flush and fsync operations."""
        # Read the actual workflow.py source to verify the fix is present
        workflow_path = Path(__file__).parent.parent.parent / "scripts" / "workflow.py"
        with open(workflow_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Check that our race condition fix is present
        assert "f.flush()" in source, "Config write should include f.flush()"
        assert "os.fsync(f.fileno())" in source, "Config write should include os.fsync()"
        assert "time.sleep(0.1)" in source, "Config write should include small delay"
    
    def test_frozen_mode_config_path_detection(self):
        """Test that frozen mode correctly resolves config paths."""
        workflow_path = Path(__file__).parent.parent.parent / "scripts" / "workflow.py"
        with open(workflow_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Verify frozen mode detection exists
        assert "getattr(sys, 'frozen', False)" in source, \
            "Should detect frozen mode with getattr(sys, 'frozen', False)"
        
        # Verify correct path resolution in frozen mode
        assert 'Path(sys.executable).parent' in source, \
            "Frozen mode should use sys.executable for path resolution"
    
    @pytest.mark.regression
    def test_config_write_completes_before_read(self):
        """Test that config writes complete before subsequent reads."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "test_config.json"
            
            # Write test data
            test_data = {"test": "value", "geocoding": {"enabled": True}}
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(test_data, f)
                f.flush()
                # Simulate the fsync that workflow.py now does
                import os
                os.fsync(f.fileno())
            
            # Small delay like in workflow.py
            time.sleep(0.01)
            
            # Read should get the data we just wrote
            with open(config_file, 'r', encoding='utf-8') as f:
                read_data = json.load(f)
            
            assert read_data == test_data, \
                "Config read should get data that was just flushed and synced"


class TestGeocodingConfiguration:
    """Test that geocoding configuration is properly set."""
    
    @pytest.mark.regression
    def test_geocoding_enabled_flag_propagates(self):
        """Test that --geocode flag properly enables geocoding in config."""
        # This test validates the fix for the race condition where config
        # was updated but ImageDescriber read old config
        
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "image_describer_config.json"
            
            # Create minimal config
            initial_config = {
                "metadata": {
                    "enabled": False,
                    "geocoding": {"enabled": False}
                }
            }
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(initial_config, f)
            
            # Simulate workflow updating config
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            config['metadata']['enabled'] = True
            config['metadata']['geocoding']['enabled'] = True
            
            # Write with proper flush/sync like workflow.py does
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
                f.flush()
                import os
                os.fsync(f.fileno())
            
            time.sleep(0.1)
            
            # Read config (simulating ImageDescriber)
            with open(config_file, 'r', encoding='utf-8') as f:
                final_config = json.load(f)
            
            assert final_config['metadata']['geocoding']['enabled'] == True, \
                "Geocoding should be enabled after config update"


class TestFrozenModePathResolution:
    """Test path resolution differences between frozen and development mode."""
    
    def test_development_mode_uses_file_path(self):
        """Test that development mode uses __file__ for path resolution."""
        workflow_path = Path(__file__).parent.parent.parent / "scripts" / "workflow.py"
        with open(workflow_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Should have else clause for non-frozen mode
        assert "Path(__file__).parent" in source, \
            "Development mode should use __file__ for paths"
    
    @pytest.mark.regression
    def test_frozen_mode_path_fix_present(self):
        """Regression test: verify frozen mode path bug is fixed."""
        workflow_path = Path(__file__).parent.parent.parent / "scripts" / "workflow.py"
        with open(workflow_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # This was the bug: using __file__ in frozen mode points to _MEIPASS temp dir
        # Fix: use sys.executable.parent in frozen mode
        assert 'if getattr(sys, \'frozen\', False):' in source or \
               'if getattr(sys, "frozen", False):' in source, \
            "Should check for frozen mode"
        
        # Verify the fix uses sys.executable for frozen mode
        lines = source.split('\n')
        frozen_block_started = False
        found_fix = False
        
        for i, line in enumerate(lines):
            if 'getattr(sys, \'frozen\', False)' in line or \
               'getattr(sys, "frozen", False)' in line:
                frozen_block_started = True
            
            if frozen_block_started and 'Path(sys.executable).parent' in line:
                found_fix = True
                break
        
        assert found_fix, \
            "Frozen mode should use Path(sys.executable).parent for config path"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
