#!/usr/bin/env python3
"""
Unit tests for identify_gallery_content.py

Tests the gallery content identification tool's core functionality.
"""

import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add parent directory to path to import the module
sys.path.insert(0, str(Path(__file__).parent.parent))
from identify_gallery_content import (
    GalleryContentIdentifier,
    build_config_from_args,
    load_config_file
)


class TestKeywordNormalization:
    """Test keyword normalization and matching."""
    
    def test_case_insensitive_normalization(self):
        """Test that case insensitive mode normalizes keywords."""
        config = {
            'gallery_name': 'Test',
            'content_rules': {
                'required_keywords': ['Water', 'SUN'],
                'case_sensitive': False
            }
        }
        identifier = GalleryContentIdentifier(config)
        
        assert identifier.required_keywords == ['water', 'sun']
    
    def test_case_sensitive_normalization(self):
        """Test that case sensitive mode preserves keywords."""
        config = {
            'gallery_name': 'Test',
            'content_rules': {
                'required_keywords': ['Water', 'SUN'],
                'case_sensitive': True
            }
        }
        identifier = GalleryContentIdentifier(config)
        
        assert identifier.required_keywords == ['Water', 'SUN']


class TestScoring:
    """Test the scoring system."""
    
    def test_required_keywords_all_match(self):
        """Test scoring when all required keywords match."""
        config = {
            'gallery_name': 'Test',
            'content_rules': {
                'required_keywords': ['water', 'sun'],
                'case_sensitive': False
            }
        }
        identifier = GalleryContentIdentifier(config)
        
        description = "The sun reflects on the water creating beautiful light."
        metadata = {'provider': 'test', 'model': 'test', 'prompt_style': 'test'}
        
        score, details = identifier.score_description(description, metadata)
        
        assert score > 0
        assert len(details['required_matches']) == 2
        assert 'water' in details['required_matches']
        assert 'sun' in details['required_matches']
        assert details['passes_filters'] is True
    
    def test_required_keywords_missing(self):
        """Test that missing required keyword returns zero score."""
        config = {
            'gallery_name': 'Test',
            'content_rules': {
                'required_keywords': ['water', 'sun'],
                'case_sensitive': False
            }
        }
        identifier = GalleryContentIdentifier(config)
        
        description = "The mountain peak is covered in snow."
        metadata = {'provider': 'test', 'model': 'test', 'prompt_style': 'test'}
        
        score, details = identifier.score_description(description, metadata)
        
        assert score == 0.0
        assert details['passes_filters'] is False
    
    def test_excluded_keywords(self):
        """Test that excluded keywords disqualify images."""
        config = {
            'gallery_name': 'Test',
            'content_rules': {
                'required_keywords': ['water'],
                'excluded_keywords': ['indoor'],
                'case_sensitive': False
            }
        }
        identifier = GalleryContentIdentifier(config)
        
        description = "Indoor pool with crystal clear water."
        metadata = {'provider': 'test', 'model': 'test', 'prompt_style': 'test'}
        
        score, details = identifier.score_description(description, metadata)
        
        assert score < 0
        assert 'indoor' in details['excluded_matches']
        assert details['passes_filters'] is False
    
    def test_preferred_keywords_bonus(self):
        """Test that preferred keywords add bonus points."""
        config = {
            'gallery_name': 'Test',
            'content_rules': {
                'required_keywords': ['water'],
                'preferred_keywords': ['sunset', 'reflection'],
                'case_sensitive': False
            }
        }
        identifier = GalleryContentIdentifier(config)
        
        # Description with required only
        desc1 = "Water is present."
        metadata = {'provider': 'test', 'model': 'test', 'prompt_style': 'test'}
        score1, _ = identifier.score_description(desc1, metadata)
        
        # Description with required + preferred
        desc2 = "Water with beautiful sunset reflection."
        score2, details2 = identifier.score_description(desc2, metadata)
        
        assert score2 > score1
        assert len(details2['preferred_matches']) == 2
    
    def test_min_keyword_matches(self):
        """Test minimum keyword match threshold."""
        config = {
            'gallery_name': 'Test',
            'content_rules': {
                'required_keywords': [],
                'preferred_keywords': ['water', 'sun', 'sunset'],
                'min_keyword_matches': 2,
                'case_sensitive': False
            }
        }
        identifier = GalleryContentIdentifier(config)
        
        # Only 1 match - should fail
        desc1 = "The water is calm."
        metadata = {'provider': 'test', 'model': 'test', 'prompt_style': 'test'}
        score1, details1 = identifier.score_description(desc1, metadata)
        assert score1 == 0.0
        assert details1['passes_filters'] is False
        
        # 2 matches - should pass
        desc2 = "The water reflects the sun."
        score2, details2 = identifier.score_description(desc2, metadata)
        assert score2 > 0
        assert details2['passes_filters'] is True
    
    def test_preferred_model_bonus(self):
        """Test bonus for preferred models."""
        config = {
            'gallery_name': 'Test',
            'content_rules': {
                'required_keywords': ['water'],
                'case_sensitive': False
            },
            'filters': {
                'preferred_models': ['claude-opus-4']
            }
        }
        identifier = GalleryContentIdentifier(config)
        
        description = "Water is present."
        
        # Non-preferred model
        metadata1 = {'provider': 'test', 'model': 'test', 'prompt_style': 'test'}
        score1, _ = identifier.score_description(description, metadata1)
        
        # Preferred model
        metadata2 = {'provider': 'claude', 'model': 'claude-opus-4', 'prompt_style': 'test'}
        score2, details2 = identifier.score_description(description, metadata2)
        
        assert score2 > score1
        assert details2['filter_bonuses'].get('preferred_model') is True
    
    def test_min_description_length(self):
        """Test minimum description length filter."""
        config = {
            'gallery_name': 'Test',
            'content_rules': {
                'required_keywords': ['water'],
                'case_sensitive': False
            },
            'filters': {
                'min_description_length': 50
            }
        }
        identifier = GalleryContentIdentifier(config)
        
        metadata = {'provider': 'test', 'model': 'test', 'prompt_style': 'test'}
        
        # Too short
        short_desc = "Water."
        score1, details1 = identifier.score_description(short_desc, metadata)
        assert score1 == 0.0
        assert details1['passes_filters'] is False
        
        # Long enough
        long_desc = "This is a beautiful scene with water that extends far beyond."
        score2, details2 = identifier.score_description(long_desc, metadata)
        assert score2 > 0
        assert details2['passes_filters'] is True


class TestWorkflowPattern:
    """Test workflow pattern matching."""
    
    def test_wildcard_matches_all(self):
        """Test that wildcard pattern matches all workflows."""
        config = {
            'gallery_name': 'Test',
            'sources': {
                'workflow_patterns': ['*']
            }
        }
        identifier = GalleryContentIdentifier(config)
        
        assert identifier._matches_workflow_pattern('wf_vacation_claude_opus', ['*'])
        assert identifier._matches_workflow_pattern('wf_test_openai_gpt4', ['*'])
    
    def test_specific_pattern_matching(self):
        """Test specific pattern matching."""
        config = {
            'gallery_name': 'Test',
            'sources': {
                'workflow_patterns': ['*vacation*', '*travel*']
            }
        }
        identifier = GalleryContentIdentifier(config)
        
        assert identifier._matches_workflow_pattern('wf_vacation_claude_opus', ['*vacation*', '*travel*'])
        assert identifier._matches_workflow_pattern('wf_europe_travel_openai', ['*vacation*', '*travel*'])
        assert not identifier._matches_workflow_pattern('wf_test_claude_opus', ['*vacation*', '*travel*'])


class TestDateRange:
    """Test date range filtering."""
    
    def test_date_within_range(self):
        """Test that dates within range pass."""
        config = {
            'gallery_name': 'Test',
            'sources': {
                'date_range': {
                    'start': '2025-10-01',
                    'end': '2025-10-31'
                }
            }
        }
        identifier = GalleryContentIdentifier(config)
        
        date_range = {'start': '2025-10-01', 'end': '2025-10-31'}
        
        assert identifier._matches_date_range('20251015_120000', date_range)
        assert identifier._matches_date_range('20251001_000000', date_range)
        assert identifier._matches_date_range('20251031_235959', date_range)
    
    def test_date_outside_range(self):
        """Test that dates outside range are filtered."""
        config = {
            'gallery_name': 'Test',
            'sources': {
                'date_range': {
                    'start': '2025-10-01',
                    'end': '2025-10-31'
                }
            }
        }
        identifier = GalleryContentIdentifier(config)
        
        date_range = {'start': '2025-10-01', 'end': '2025-10-31'}
        
        assert not identifier._matches_date_range('20250915_120000', date_range)
        assert not identifier._matches_date_range('20251101_120000', date_range)


class TestDescriptionParsing:
    """Test description block parsing."""
    
    def test_parse_complete_block(self):
        """Test parsing a complete description block."""
        config = {'gallery_name': 'Test'}
        identifier = GalleryContentIdentifier(config)
        
        block = """File: test_image.jpg
Description: A beautiful sunset over the water with golden reflections.
Provider: claude
Model: opus-4
Prompt Style: narrative
Cost: $0.001
Tokens: 150
Time: 1.2s"""
        
        result = identifier._parse_description_block(block)
        
        assert result is not None
        assert result['filename'] == 'test_image.jpg'
        assert 'sunset' in result['description']
        assert result['provider'] == 'claude'
        assert result['model'] == 'opus-4'
        assert result['prompt_style'] == 'narrative'
    
    def test_parse_minimal_block(self):
        """Test parsing a minimal description block."""
        config = {'gallery_name': 'Test'}
        identifier = GalleryContentIdentifier(config)
        
        block = """File: test_image.jpg
Description: Simple description."""
        
        result = identifier._parse_description_block(block)
        
        assert result is not None
        assert result['filename'] == 'test_image.jpg'
        assert result['description'] == 'Simple description.'
        assert result['provider'] == 'unknown'
    
    def test_parse_multiline_description(self):
        """Test parsing description with multiple lines."""
        config = {'gallery_name': 'Test'}
        identifier = GalleryContentIdentifier(config)
        
        block = """File: test_image.jpg
Description: This is a longer description
that spans multiple lines
and continues here.
Provider: claude"""
        
        result = identifier._parse_description_block(block)
        
        assert result is not None
        assert 'multiple lines' in result['description']
        assert 'continues here' in result['description']


class TestConfigurationLoading:
    """Test configuration file loading."""
    
    def test_load_valid_config(self):
        """Test loading a valid configuration file."""
        config_data = {
            'gallery_name': 'Test Gallery',
            'content_rules': {
                'required_keywords': ['water', 'sun']
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_path = Path(f.name)
        
        try:
            loaded = load_config_file(config_path)
            assert loaded['gallery_name'] == 'Test Gallery'
            assert loaded['content_rules']['required_keywords'] == ['water', 'sun']
        finally:
            config_path.unlink()
    
    def test_build_config_from_args(self):
        """Test building configuration from command-line arguments."""
        # Mock argparse Namespace
        args = Mock()
        args.name = 'Test Gallery'
        args.scan = ['./descriptions']
        args.workflow_patterns = 'vacation,travel'
        args.date_start = '2025-10-01'
        args.date_end = '2025-10-31'
        args.required = 'water,sun'
        args.keywords = 'sunset,reflection'
        args.exclude = 'indoor,night'
        args.min_matches = 2
        args.case_sensitive = False
        args.min_length = 100
        args.prompts = 'narrative,colorful'
        args.models = 'claude-opus-4'
        args.max_images = 50
        args.sort_by = 'keyword_relevance'
        args.no_metadata = False
        
        config = build_config_from_args(args)
        
        assert config['gallery_name'] == 'Test Gallery'
        assert config['sources']['directories'] == ['./descriptions']
        assert 'vacation' in config['sources']['workflow_patterns']
        assert config['sources']['date_range']['start'] == '2025-10-01'
        assert config['content_rules']['required_keywords'] == ['water', 'sun']
        assert config['content_rules']['preferred_keywords'] == ['sunset', 'reflection']
        assert config['content_rules']['excluded_keywords'] == ['indoor', 'night']
        assert config['content_rules']['min_keyword_matches'] == 2
        assert config['filters']['min_description_length'] == 100
        assert config['output']['max_images'] == 50


class TestOutputGeneration:
    """Test output generation and formatting."""
    
    def test_output_format(self):
        """Test that output has correct structure."""
        config = {
            'gallery_name': 'Test Gallery',
            'content_rules': {
                'required_keywords': ['water'],
                'preferred_keywords': ['sun'],
                'excluded_keywords': ['indoor'],
                'min_keyword_matches': 1
            },
            'output': {
                'max_images': 10
            }
        }
        identifier = GalleryContentIdentifier(config)
        
        # Add a mock candidate
        identifier.candidates = [{
            'filename': 'test.jpg',
            'score': 15.0,
            'workflow_path': './test',
            'workflow_name': 'test',
            'description': 'Water and sun',
            'match_details': {
                'required_matches': ['water'],
                'preferred_matches': ['sun'],
                'excluded_matches': [],
                'filter_bonuses': {},
                'passes_filters': True
            }
        }]
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_path = Path(f.name)
        
        try:
            identifier.save_results(output_path)
            
            with open(output_path, 'r') as f:
                output = json.load(f)
            
            assert output['gallery_name'] == 'Test Gallery'
            assert 'generated_at' in output
            assert 'configuration' in output
            assert output['total_candidates'] == 1
            assert len(output['candidates']) == 1
            assert output['candidates'][0]['filename'] == 'test.jpg'
        finally:
            output_path.unlink()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
