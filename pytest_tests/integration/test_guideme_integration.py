"""
Integration tests for guideme command generation and flag handling.

These tests validate that guideme correctly builds workflow commands with
the proper flags, especially after the geocoding default change from opt-in
(--geocode) to opt-out (--no-geocode).
"""

import pytest
import sys
from pathlib import Path

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))


class TestGuidemeStaticValidation:
    """Static code analysis tests to catch flag usage issues."""

    def test_no_old_geocode_flag_in_guideme(self):
        """Ensure guideme code doesn't use the old --geocode flag."""
        guideme_file = scripts_dir / "guided_workflow.py"
        content = guideme_file.read_text(encoding='utf-8')
        
        # Check for problematic patterns - the old flag should not exist
        assert '"--geocode"' not in content, \
            "guided_workflow.py should not use '--geocode' flag (use '--no-geocode' instead)"
        
        assert "'--geocode'" not in content, \
            "guided_workflow.py should not use '--geocode' flag (use '--no-geocode' instead)"

    def test_new_no_geocode_flag_present(self):
        """Verify the new --no-geocode flag is referenced in guideme."""
        guideme_file = scripts_dir / "guided_workflow.py"
        content = guideme_file.read_text(encoding='utf-8')
        
        # Verify new flag is present
        assert '--no-geocode' in content, \
            "guided_workflow.py should reference '--no-geocode' flag"

    def test_geocode_cache_flag_present(self):
        """Verify --geocode-cache flag is still supported."""
        guideme_file = scripts_dir / "guided_workflow.py"
        content = guideme_file.read_text(encoding='utf-8')
        
        assert '--geocode-cache' in content, \
            "guided_workflow.py should still support '--geocode-cache' flag"

    def test_geocoding_wizard_logic(self):
        """Verify the geocoding wizard section has correct logic."""
        guideme_file = scripts_dir / "guided_workflow.py"
        content = guideme_file.read_text(encoding='utf-8')
        
        # Check that metadata/geocoding section exists
        assert 'enable_metadata' in content, "Should have metadata enable logic"
        assert 'enable_geocoding' in content, "Should have geocoding enable logic"
        
        # Check that the logic adds --no-geocode when geocoding is disabled
        # This is the key fix: only add --no-geocode when explicitly disabled
        assert 'not enable_geocoding' in content or '!enable_geocoding' in content, \
            "Should check for disabled geocoding to add --no-geocode flag"


class TestGuidemePassthroughFlags:
    """Test that passthrough flags in guideme match workflow.py."""

    def test_passthrough_flags_section_exists(self):
        """Verify there's a section defining allowed passthrough flags."""
        guideme_file = scripts_dir / "guided_workflow.py"
        content = guideme_file.read_text(encoding='utf-8')
        
        # Look for the section around line 316 where allowed flags are defined
        assert 'timeout' in content.lower(), "Should reference timeout flag"

    def test_guideme_command_building(self):
        """Verify command building section constructs args correctly."""
        guideme_file = scripts_dir / "guided_workflow.py"
        content = guideme_file.read_text(encoding='utf-8')
        
        # Check for extra_workflow_args usage
        assert 'extra_workflow_args' in content, \
            "Should have extra_workflow_args for passthrough flags"
        
        # Check that args are extended to the command
        assert 'extend(extra_workflow_args)' in content or 'extra_workflow_args.append' in content, \
            "Should add extra workflow args to command"


class TestWorkflowGeocodingDefaults:
    """Verify workflow.py has correct geocoding defaults."""

    def test_workflow_has_no_geocode_flag(self):
        """Verify workflow.py uses --no-geocode (not --geocode)."""
        workflow_file = scripts_dir / "workflow.py"
        content = workflow_file.read_text(encoding='utf-8')
        
        # Should have --no-geocode argument
        assert '--no-geocode' in content, \
            "workflow.py should have --no-geocode flag"

    def test_workflow_geocoding_default_true(self):
        """Verify geocoding is enabled by default in workflow.py."""
        workflow_file = scripts_dir / "workflow.py"
        content = workflow_file.read_text(encoding='utf-8')
        
        # Look for the enable_geocoding default value
        # It should be: enable_geocoding: bool = True
        import re
        
        # Find enable_geocoding initialization with default value
        pattern = r'enable_geocoding\s*:\s*bool\s*=\s*(True|False)'
        matches = re.findall(pattern, content)
        
        assert len(matches) > 0, "Should find enable_geocoding initialization"
        assert matches[0] == 'True', \
            f"enable_geocoding should default to True, found: {matches[0]}"

    def test_workflow_no_old_geocode_flag(self):
        """Verify workflow.py doesn't have the old --geocode flag."""
        workflow_file = scripts_dir / "workflow.py"
        content = workflow_file.read_text(encoding='utf-8')
        
        # Check for add_argument with --geocode (should NOT exist)
        import re
        pattern = r'add_argument\(["\']--geocode["\']'
        matches = re.findall(pattern, content)
        
        # Filter out --geocode-cache matches
        geocode_only = [m for m in matches if '--geocode-cache' not in m]
        
        assert len(geocode_only) == 0, \
            f"workflow.py should not have '--geocode' flag, found: {geocode_only}"


class TestIntegrationBetweenGuidemeAndWorkflow:
    """Integration tests between guideme and workflow."""

    def test_guideme_flags_match_workflow_flags(self):
        """Verify flags used by guideme are valid in workflow.py."""
        guideme_file = scripts_dir / "guided_workflow.py"
        workflow_file = scripts_dir / "workflow.py"
        
        guideme_content = guideme_file.read_text(encoding='utf-8')
        workflow_content = workflow_file.read_text(encoding='utf-8')
        
        # Extract flags that guideme adds to commands
        import re
        
        # Find patterns like '--flag' in guideme
        guideme_flags = set(re.findall(r'["\'](--.+?)["\']', guideme_content))
        
        # Filter to workflow-related flags (not idt subcommands)
        workflow_flags = {f for f in guideme_flags if f.startswith('--') and 
                         not f.startswith('--idt-') and 
                         f != '--help' and f != '--version'}
        
        # Each flag should exist in workflow.py
        for flag in workflow_flags:
            if flag in ['--no-geocode', '--geocode-cache', '--timeout', 
                       '--no-video-extraction', '--no-image-conversion',
                       '--no-description', '--no-html-generation',
                       '--provider', '--model', '--output-dir', '--api-key-file',
                       '--name', '--prompt-style']:
                # These are valid flags - should exist in workflow
                assert flag in workflow_content, \
                    f"Flag {flag} used by guideme should exist in workflow.py"

    def test_geocoding_behavior_consistency(self):
        """Verify geocoding behavior is consistent between guideme and workflow."""
        guideme_file = scripts_dir / "guided_workflow.py"
        workflow_file = scripts_dir / "workflow.py"
        
        guideme_content = guideme_file.read_text(encoding='utf-8')
        workflow_content = workflow_file.read_text(encoding='utf-8')
        
        # Both should reference --no-geocode (not --geocode)
        assert '--no-geocode' in guideme_content, "guideme should use --no-geocode"
        assert '--no-geocode' in workflow_content, "workflow should use --no-geocode"
        
        # Neither should use old --geocode flag
        assert '"--geocode"' not in guideme_content and "'--geocode'" not in guideme_content, \
            "guideme should not use old --geocode flag"


if __name__ == "__main__":
    # Allow running directly for quick testing
    pytest.main([__file__, "-v"])
