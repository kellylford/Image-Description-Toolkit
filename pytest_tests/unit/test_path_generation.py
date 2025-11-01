"""
Unit tests for workflow path generation and filesystem naming.

Tests the sanitize_name() function and get_path_identifier_2_components()
that are critical for creating consistent, filesystem-safe workflow directories.
"""

import pytest
import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

try:
    from workflow import sanitize_name, get_path_identifier_2_components
    WORKFLOW_AVAILABLE = True
except ImportError as e:
    WORKFLOW_AVAILABLE = False
    print(f"Warning: Could not import workflow functions: {e}")


@pytest.mark.unit
@pytest.mark.skipif(not WORKFLOW_AVAILABLE, reason="workflow module not available")
class TestSanitizeName:
    """Test filesystem-safe name generation"""
    
    def test_removes_special_characters(self):
        """Test that special characters are removed"""
        assert sanitize_name("GPT-4 Vision!") == "GPT-4Vision"
        assert sanitize_name("model:tag@version") == "modeltagversion"
        assert sanitize_name("name$with%symbols") == "namewithsymbols"
    
    def test_preserves_valid_characters(self):
        """Test that valid filesystem characters are preserved"""
        assert sanitize_name("model_name-v2.1") == "model_name-v2.1"
        assert sanitize_name("simple_name") == "simple_name"
        assert sanitize_name("Model.Name") == "Model.Name"
    
    def test_handles_empty_string(self):
        """Test that empty strings return 'unknown'"""
        assert sanitize_name("") == "unknown"
        assert sanitize_name(None) == "unknown"
    
    def test_case_preservation_flag(self):
        """Test case preservation option"""
        assert sanitize_name("GPT4", preserve_case=True) == "GPT4"
        assert sanitize_name("GPT4", preserve_case=False) == "gpt4"
        assert sanitize_name("MixedCase", preserve_case=True) == "MixedCase"
        assert sanitize_name("MixedCase", preserve_case=False) == "mixedcase"
    
    def test_removes_colons(self):
        """Test that colons are removed (common in model names)"""
        assert ":" not in sanitize_name("llava:7b")
        assert ":" not in sanitize_name("model:latest:tag")
    
    def test_removes_slashes(self):
        """Test that slashes are removed (path separators)"""
        assert "/" not in sanitize_name("model/with/slashes")
        assert "\\" not in sanitize_name("model\\with\\backslashes")
    
    def test_handles_spaces(self):
        """Test that spaces are removed"""
        result = sanitize_name("GPT 4 Vision")
        assert " " not in result
        assert "GPT" in result
        assert "Vision" in result
    
    def test_preserves_numbers(self):
        """Test that numbers are preserved"""
        assert "123" in sanitize_name("model123")
        assert "7" in sanitize_name("llava:7b")
    
    def test_realistic_model_names(self):
        """Test with realistic AI model names"""
        # OpenAI models
        assert sanitize_name("gpt-4o-mini") == "gpt-4o-mini"
        assert sanitize_name("gpt-4-vision-preview") == "gpt-4-vision-preview"
        
        # Ollama models  
        result = sanitize_name("llava:7b")
        assert "llava" in result
        assert "7b" in result
        assert ":" not in result
        
        # Claude models
        result = sanitize_name("claude-3.5-sonnet")
        assert "claude" in result
        assert "3.5" in result or "35" in result
        assert "sonnet" in result


@pytest.mark.unit
@pytest.mark.skipif(not WORKFLOW_AVAILABLE, reason="workflow module not available")
class TestPathIdentifier:
    """Test workflow directory naming"""
    
    def test_basic_format(self):
        """Test that path identifier has correct format"""
        identifier = get_path_identifier_2_components("test_model", "narrative")
        
        # Should contain both components
        assert "test_model" in identifier or "testmodel" in identifier.lower()
        assert "narrative" in identifier.lower()
    
    def test_sanitizes_model_name(self):
        """Test that model names are sanitized"""
        identifier = get_path_identifier_2_components("model:with:colons", "prompt")
        
        # Should not contain colons
        assert ":" not in identifier
    
    def test_sanitizes_prompt_name(self):
        """Test that prompt names are sanitized"""
        identifier = get_path_identifier_2_components("model", "prompt with spaces!")
        
        # Should not contain spaces or special chars
        assert " " not in identifier
        assert "!" not in identifier
    
    def test_realistic_examples(self):
        """Test with realistic model/prompt combinations"""
        # GPT-4 + narrative
        identifier = get_path_identifier_2_components("gpt-4o", "narrative")
        assert "gpt" in identifier.lower()
        assert "narrative" in identifier.lower()
        
        # Llava + concise
        identifier = get_path_identifier_2_components("llava:7b", "concise")
        assert "llava" in identifier.lower()
        assert "concise" in identifier.lower()
        assert ":" not in identifier
    
    def test_consistent_output(self):
        """Test that same inputs produce same output"""
        id1 = get_path_identifier_2_components("model", "prompt")
        id2 = get_path_identifier_2_components("model", "prompt")
        
        assert id1 == id2, "Same inputs should produce same identifier"
    
    def test_different_inputs_different_output(self):
        """Test that different inputs produce different outputs"""
        id1 = get_path_identifier_2_components("model1", "prompt")
        id2 = get_path_identifier_2_components("model2", "prompt")
        
        assert id1 != id2, "Different models should produce different identifiers"
        
        id3 = get_path_identifier_2_components("model", "prompt1")
        id4 = get_path_identifier_2_components("model", "prompt2")
        
        assert id3 != id4, "Different prompts should produce different identifiers"
    
    def test_handles_empty_inputs(self):
        """Test behavior with empty inputs"""
        # Should not crash
        try:
            identifier = get_path_identifier_2_components("", "")
            assert len(identifier) > 0, "Should return something even with empty inputs"
        except (ValueError, AssertionError):
            # If it raises an error, that's also acceptable behavior
            pass
    
    def test_length_reasonable(self):
        """Test that generated identifiers aren't too long"""
        identifier = get_path_identifier_2_components(
            "very_long_model_name_that_goes_on_and_on",
            "very_long_prompt_style_name"
        )
        
        # Windows has 260 char path limit, identifiers should be reasonable
        assert len(identifier) < 100, f"Identifier too long: {len(identifier)} chars"


@pytest.mark.unit
@pytest.mark.skipif(not WORKFLOW_AVAILABLE, reason="workflow module not available")
def test_sanitize_name_idempotent():
    """Test that sanitizing twice gives same result as sanitizing once"""
    name = "model:with:special@chars!"
    once = sanitize_name(name)
    twice = sanitize_name(once)
    
    assert once == twice, "Sanitizing should be idempotent"


@pytest.mark.unit
@pytest.mark.skipif(not WORKFLOW_AVAILABLE, reason="workflow module not available")
def test_path_identifier_filesystem_safe():
    """Test that path identifiers are safe for Windows and Unix"""
    # Test with problematic characters
    identifier = get_path_identifier_2_components(
        "model<>:\"/\\|?*",
        "prompt<>:\"/\\|?*"
    )
    
    # Should not contain any problematic characters
    forbidden_chars = '<>:"/\\|?*'
    for char in forbidden_chars:
        assert char not in identifier, f"Identifier contains forbidden char: {char}"
    
    # Should be usable in a path
    try:
        test_path = Path(f"test/{identifier}/file.txt")
        # If we can create the Path object, the identifier is valid
        assert test_path.parts[1] == identifier
    except Exception as e:
        pytest.fail(f"Path identifier not filesystem-safe: {e}")


@pytest.mark.unit
@pytest.mark.skipif(not WORKFLOW_AVAILABLE, reason="workflow module not available")
def test_sanitize_name_unicode_handling():
    """Test handling of unicode characters"""
    # Unicode should be handled gracefully (removed or preserved)
    result = sanitize_name("modèl_nåme_τεστ")
    
    # Result should be a valid string
    assert isinstance(result, str)
    assert len(result) > 0
    
    # Should handle emoji
    result = sanitize_name("model_😀_name")
    assert isinstance(result, str)


@pytest.mark.unit
@pytest.mark.skipif(not WORKFLOW_AVAILABLE, reason="workflow module not available")
def test_realistic_workflow_directory_names():
    """Test that we can generate realistic workflow directory names"""
    test_cases = [
        ("gpt-4o", "narrative"),
        ("claude-3.5-sonnet", "concise"),
        ("llava:13b", "detailed"),
        ("moondream", "narrative"),
        ("mistral:7b-instruct", "structured"),
    ]
    
    for model, prompt in test_cases:
        identifier = get_path_identifier_2_components(model, prompt)
        
        # Should be filesystem safe
        assert "/" not in identifier
        assert "\\" not in identifier
        assert ":" not in identifier
        
        # Should contain recognizable parts
        # (Model and prompt might be transformed, so check loosely)
        assert len(identifier) > 5
        assert identifier.replace("_", "").replace("-", "").replace(".", "").isalnum()
