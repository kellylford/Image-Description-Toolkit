#!/usr/bin/env python3
"""
Model Reliability Validator for OpenAI Models

Tests a subset of images across all GPT-5 models to identify which are reliable
for production use. Based on findings from gpt-5-nano issues (28-40% empty responses).

Usage:  python validate_openai_models.py [--images N]

Reports:
- Success rate for each model
- Average tokens per successful response
- Any empty responses or errors
- Recommended models for production
"""

import sys
import os
from pathlib import Path
import json
import base64
from datetime import datetime
from typing import Dict, List, Tuple

# Add scripts to path for config loader
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR / 'scripts'))

from config_loader import load_json_config

def load_api_key():
    """Load OpenAI API key from config"""
    config, config_path, source = load_json_config('image_describer_config.json')
    
    if not config:
        print("❌ Error: Could not load image_describer_config.json")
        return None
    
    api_key = config.get('api_keys', {}).get('OpenAI')
    if not api_key:
        print("❌ Error: No OpenAI API key found in config")
        print(f"   Config file: {config_path}")
        return None
    
    return api_key


def encode_image_base64(image_path: Path) -> str:
    """Encode image to base64"""
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def test_model(client, model_id: str, test_images: List[Path]) -> Dict:
    """
    Test a single model with a set of images
    
    Returns:
        {
            'model': model_id,
            'total': count,
            'successful': count,
            'empty': count,
            'errors': count,
            'success_rate': percentage,
            'avg_tokens': float,
            'details': [...]
        }
    """
    print(f"\n{'='*70}")
    print(f"Testing: {model_id}")
    print(f"{'='*70}")
    
    results = {
        'model': model_id,
        'total': len(test_images),
        'successful': 0,
        'empty': 0,
        'errors': 0,
        'success_rate': 0.0,
        'avg_tokens': 0.0,
        'total_tokens': 0,
        'details': []
    }
    
    for idx, img_path in enumerate(test_images, 1):
        img_name = img_path.name
        
        try:
            # Encode image
            base64_img = encode_image_base64(img_path)
            
            # Make request
            response = client.chat.completions.create(
                model=model_id,
                max_completion_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe this image in detail."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_img}"
                            }
                        }
                    ]
                }]
            )
            
            # Extract data
            choice = response.choices[0]
            content = choice.message.content or ""
            finish_reason = choice.finish_reason
            tokens = response.usage.completion_tokens
            
            # Classify result
            if len(content.strip()) == 0:
                status = "❌ EMPTY"
                results['empty'] += 1
            else:
                status = "✓ OK"
                results['successful'] += 1
                results['total_tokens'] += tokens
            
            print(f"[{idx:2d}/{len(test_images)}] {status:8s} | {img_name:20s} | finish={finish_reason:6s} | tokens={tokens:4d} | len={len(content):4d}")
            
            results['details'].append({
                'image': img_name,
                'status': 'empty' if len(content.strip()) == 0 else 'success',
                'finish_reason': finish_reason,
                'tokens': tokens,
                'content_length': len(content)
            })
            
        except Exception as e:
            print(f"[{idx:2d}/{len(test_images)}] ⚠️  ERROR | {img_name:20s} | {str(e)[:50]}")
            results['errors'] += 1
            results['details'].append({
                'image': img_name,
                'status': 'error',
                'error': str(e)
            })
    
    # Calculate success rate
    results['success_rate'] = (results['successful'] / results['total'] * 100) if results['total'] > 0 else 0
    
    # Calculate average tokens
    if results['successful'] > 0:
        results['avg_tokens'] = results['total_tokens'] / results['successful']
    
    # Print summary
    print(f"\n{'─'*70}")
    print(f"SUMMARY: {model_id}")
    print(f"  Success: {results['successful']}/{results['total']} ({results['success_rate']:.1f}%)")
    print(f"  Empty  : {results['empty']}")
    print(f"  Errors : {results['errors']}")
    if results['successful'] > 0:
        print(f"  Avg tokens: {results['avg_tokens']:.0f}")
    print(f"{'─'*70}")
    
    return results


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate OpenAI model reliability')
    parser.add_argument('--images', type=int, default=20, 
                       help='Number of test images to use (default: 20)')
    args = parser.parse_args()
    
    print("=" * 70)
    print("OpenAI Model Reliability Validator")
    print("=" * 70)
    
    # Load API key
    api_key = load_api_key()
    if not api_key:
        return 1
    
    print(f"✓ API key loaded (length: {len(api_key)} chars)")
    
    # Initialize OpenAI client
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        print(f"✓ OpenAI client initialized")
    except Exception as e:
        print(f"❌ Error initializing OpenAI client: {e}")
        return 1
    
    # Load test images
    test_dir = SCRIPT_DIR / 'testimages'
    if not test_dir.exists():
        print(f"❌ Test images directory not found: {test_dir}")
        return 1
    
    # Get image files
    image_files = sorted([
        f for f in test_dir.iterdir()
        if f.suffix.lower() in ['.jpg', '.jpeg', '.png']
    ])
    
    if len(image_files) == 0:
        print(f"❌ No test images found in: {test_dir}")
        return 1
    
    # Limit to requested number
    test_images = image_files[:args.images]
    print(f"✓ Loaded {len(test_images)} test images from {test_dir}")
    
    # Models to test - focus on GPT-5 series and known-good gpt-4o
    models_to_test = [
        # Known good (baseline)
        "gpt-4o",
        "gpt-4o-mini",
        
        # GPT-5 series - test all tiers
        "gpt-5-nano",          # Known problematic (28-40% empty)
        "gpt-5-mini",
        "gpt-5",
        "gpt-5-pro",
        "gpt-5.1",
        "gpt-5.2",
        "gpt-5.2-pro",
    ]
    
    print(f"\nTesting {len(models_to_test)} models:\n")
    for i, m in enumerate(models_to_test, 1):
        print(f"  {i}. {m}")
    print()
    
    # Run tests
    all_results = []
    failed_models = []
    
    for model_id in models_to_test:
        try:
            result = test_model(client, model_id, test_images)
            all_results.append(result)
            
            # Track models with >5% failure rate
            if result['success_rate'] < 95.0:
                failed_models.append((model_id, result['success_rate']))
                
        except KeyboardInterrupt:
            print("\n\n⚠️  Testing interrupted by user")
            break
        except Exception as e:
            print(f"\n❌ Fatal error testing {model_id}: {e}")
            all_results.append({
                'model': model_id,
                'total': len(test_images),
                'successful': 0,
                'empty': 0,
                'errors': len(test_images),
                'success_rate': 0.0,
                'avg_tokens': 0.0,
                'details': []
            })
            failed_models.append((model_id, 0.0))
    
    # Print final summary
    print(f"\n{'='*70}")
    print("FINAL SUMMARY")
    print(f"{'='*70}\n")
    
    print(f"{'Model':<25} {'Success Rate':>12} {'Empty':>8} {'Errors':>8} {'Avg Tokens':>12}")
    print(f"{'-'*25} {'-'*12} {'-'*8} {'-'*8} {'-'*12}")
    
    for result in all_results:
        model = result['model']
        success = f"{result['success_rate']:.1f}%"
        empty = result['empty']
        errors = result['errors']
        avg_tok = f"{result['avg_tokens']:.0f}" if result['avg_tokens'] > 0 else "N/A"
        
        # Highlight problematic models
        if result['success_rate'] < 95.0:
            marker = "⚠️  "
        else:
            marker = "✓  "
        
        print(f"{marker}{model:<23} {success:>12} {empty:>8} {errors:>8} {avg_tok:>12}")
    
    print(f"\n{'='*70}")
    print("RECOMMENDATIONS")
    print(f"{'='*70}\n")
    
    # Categorize models
    reliable = [r for r in all_results if r['success_rate'] >= 99.0]
    usable = [r for r in all_results if 95.0 <= r['success_rate'] < 99.0]
    unreliable = [r for r in all_results if r['success_rate'] < 95.0]
    
    if reliable:
        print("✓ RELIABLE (≥99% success - recommended for production):")
        for r in reliable:
            print(f"  - {r['model']:<25} ({r['success_rate']:.1f}%)")
    
    if usable:
        print("\n⚠️  USABLE (95-99% success - acceptable with retry logic):")
        for r in usable:
            print(f"  - {r['model']:<25} ({r['success_rate']:.1f}%)")
    
    if unreliable:
        print("\n❌ UNRELIABLE (<95% success - DO NOT USE in production):")
        for r in unreliable:
            print(f"  - {r['model']:<25} ({r['success_rate']:.1f}%)")
    
    # Save detailed results
    output_file = SCRIPT_DIR / f"model_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'test_images_count': len(test_images),
            'models_tested': len(all_results),
            'results': all_results,
            'reliable': [r['model'] for r in reliable],
            'usable': [r['model'] for r in usable],
            'unreliable': [r['model'] for r in unreliable]
        }, f, indent=2)
    
    print(f"\n✓ Detailed results saved to: {output_file.name}")
    print(f"{'='*70}\n")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
