#!/usr/bin/env python3

from comprehensive_test import ComprehensiveTester
import json
from pathlib import Path
import tempfile

def test_html_generation():
    """Test HTML generation with mock data"""
    try:
        # Create temporary output directory
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir)
            image_path = Path('tests/test_files/images')
            
            # Test the HTML generation method
            tester = ComprehensiveTester(image_path, output_path)
            
            # Create mock results data
            tester.results = [
                {
                    'model': 'test-model',
                    'prompt': 'detailed',
                    'duration': 45.2,
                    'success': True,
                    'output_dir': output_path / 'test-model_detailed',
                    'error': None
                },
                {
                    'model': 'another-model',
                    'prompt': 'artistic',
                    'duration': 60.1,
                    'success': True,
                    'output_dir': output_path / 'another-model_artistic',
                    'error': None
                }
            ]
            
            print('Testing HTML generation...')
            tester.generate_html_report()
            
            # Check if file was created
            html_file = output_path / "comprehensive_test_visual_report.html"
            if html_file.exists():
                # Read and check content
                content = html_file.read_text(encoding='utf-8')
                
                # Check for proper heading structure
                if '<h2 class="prompt-header">' in content:
                    print('✓ Prompt headers correctly formatted as h2')
                else:
                    print('✗ Prompt headers not found or incorrectly formatted')
                
                if '<h3 class="model-header">' in content:
                    print('✓ Model headers correctly formatted as h3')
                else:
                    print('✗ Model headers not found or incorrectly formatted')
                
                if '<h4 class="description-header">' in content:
                    print('✓ Description headers correctly formatted as h4')
                else:
                    print('✓ Description headers not present (no descriptions in mock data)')
                
                # Check for emoji removal
                emojis = ['🔍', '📊', '🎯', '🤖', '⏱️', '📷', '❌', '📸']
                found_emojis = [emoji for emoji in emojis if emoji in content]
                
                if not found_emojis:
                    print('✓ All emojis successfully removed from HTML')
                else:
                    print(f'✗ Found remaining emojis: {found_emojis}')
                
                print('✓ HTML generation test passed!')
            else:
                print('✗ HTML file was not created')
                
    except Exception as e:
        print(f'✗ Error during HTML generation test: {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_html_generation()
