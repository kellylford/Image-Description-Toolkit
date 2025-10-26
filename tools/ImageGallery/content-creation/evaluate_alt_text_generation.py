#!/usr/bin/env python3
"""
Alt Text Generation Evaluation Script

This script randomly selects 5 images from the gallery data and generates alt text using:
1. The original AI that created the description
2. Claude Haiku 3.5 for comparison

Results are logged for evaluation of different approaches.

Usage:
    python evaluate_alt_text_generation.py [--descriptions-dir PATH]
"""

import os
import sys
import json
import random
import re
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import argparse

# For API calls
import requests
import time


def setup_logging(output_dir: Path) -> logging.Logger:
    """Set up logging to file with detailed formatting."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = output_dir / f'alt_text_evaluation_{timestamp}.log'
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Alt Text Evaluation Log: {log_file}")
    return logger


def get_claude_api_key() -> Optional[str]:
    """Get Claude API key from environment."""
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable not set")
        print("Please run: set ANTHROPIC_API_KEY=your_api_key_here")
        return None
    return api_key


def call_claude_api(api_key: str, prompt: str, model: str = "claude-3-5-haiku-20241022") -> Optional[str]:
    """Call Claude API for alt text generation."""
    url = "https://api.anthropic.com/v1/messages"
    
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01"
    }
    
    data = {
        "model": model,
        "max_tokens": 100,  # Short alt text doesn't need many tokens
        "temperature": 0.1,  # Lower temperature for more consistent results
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        alt_text = result['content'][0]['text'].strip()
        
        # Log token usage for cost tracking
        usage = result.get('usage', {})
        logging.getLogger(__name__).info(f"Claude API - Tokens: {usage.get('input_tokens', 0)} input + {usage.get('output_tokens', 0)} output")
        
        return alt_text
    
    except requests.exceptions.RequestException as e:
        logging.getLogger(__name__).error(f"Claude API error: {e}")
        return None
    except Exception as e:
        logging.getLogger(__name__).error(f"Unexpected error calling Claude API: {e}")
        return None


def call_openai_api(api_key: str, prompt: str, model: str = "gpt-4o-mini") -> Optional[str]:
    """Call OpenAI API for alt text generation."""
    url = "https://api.openai.com/v1/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    data = {
        "model": model,
        "max_tokens": 100,
        "temperature": 0.1,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        alt_text = result['choices'][0]['message']['content'].strip()
        
        # Log token usage
        usage = result.get('usage', {})
        logging.getLogger(__name__).info(f"OpenAI API - Tokens: {usage.get('prompt_tokens', 0)} input + {usage.get('completion_tokens', 0)} output")
        
        return alt_text
    
    except requests.exceptions.RequestException as e:
        logging.getLogger(__name__).error(f"OpenAI API error: {e}")
        return None
    except Exception as e:
        logging.getLogger(__name__).error(f"Unexpected error calling OpenAI API: {e}")
        return None


def create_alt_text_prompt(description: str) -> str:
    """Create a standardized prompt for alt text generation."""
    return f"""Please create concise alt text (20-50 words) for this image description. Focus on:
- Main subject and key visual elements
- Setting/location if important
- Prominent colors or lighting
- Avoid interpretation, just describe what's visible
- Make it useful for screen reader users

Original description:
{description}

Alt text (20-50 words):"""


def extract_first_sentence_fallback(description: str) -> str:
    """Fallback method: Extract first sentence and truncate if needed."""
    # Get first sentence
    sentences = re.split(r'[.!?]+', description)
    first_sentence = sentences[0].strip() + '.'
    
    # If too long, truncate at reasonable word boundary
    words = first_sentence.split()
    if len(words) > 50:
        truncated = ' '.join(words[:45]) + '...'
        return truncated
    
    return first_sentence


def find_random_images_with_descriptions(descriptions_dir: Path, count: int = 5) -> List[Dict]:
    """Find random images that have descriptions available."""
    logger = logging.getLogger(__name__)
    
    # Find all workflow directories
    workflow_dirs = [d for d in descriptions_dir.iterdir() 
                    if d.is_dir() and d.name.startswith('wf_25imagetest')]
    
    logger.info(f"Found {len(workflow_dirs)} workflow directories")
    
    # Collect all image descriptions
    all_descriptions = {}
    
    for workflow_dir in workflow_dirs:
        desc_file = workflow_dir / 'descriptions' / 'image_descriptions.txt'
        if not desc_file.exists():
            continue
            
        # Parse workflow info
        parts = workflow_dir.name.split('_')
        if len(parts) < 6:
            continue
            
        provider = parts[2]
        model = '_'.join(parts[3:-2])  # Handle multi-part model names
        prompt = parts[-2]
        
        # Read descriptions
        try:
            with open(desc_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse descriptions
            blocks = re.split(r'\n-{40,}\n', content)
            for block in blocks:
                if not block.strip():
                    continue
                    
                file_match = re.search(r'^File:\s*(.+?)$', block, re.MULTILINE)
                desc_match = re.search(r'Description:\s*(.*?)\s*Timestamp:', block, re.DOTALL)
                
                if file_match and desc_match:
                    filename = os.path.basename(file_match.group(1).strip())
                    description = desc_match.group(1).strip()
                    
                    if filename not in all_descriptions:
                        all_descriptions[filename] = {}
                    
                    config_key = f"{provider}_{model}_{prompt}"
                    all_descriptions[filename][config_key] = {
                        'provider': provider,
                        'model': model,
                        'prompt': prompt,
                        'description': description,
                        'workflow_dir': workflow_dir.name
                    }
        
        except Exception as e:
            logger.error(f"Error reading {desc_file}: {e}")
    
    # Find images that have multiple descriptions (for variety)
    good_images = [(filename, descriptions) for filename, descriptions in all_descriptions.items() 
                   if len(descriptions) >= 2]  # At least 2 different configurations
    
    if len(good_images) < count:
        logger.warning(f"Only found {len(good_images)} images with multiple descriptions, using all available")
        selected = good_images
    else:
        selected = random.sample(good_images, count)
    
    logger.info(f"Selected {len(selected)} images for evaluation")
    return selected


def generate_alt_text_for_image(filename: str, descriptions: Dict, claude_api_key: str) -> Dict:
    """Generate alt text using different approaches for one image."""
    logger = logging.getLogger(__name__)
    results = {
        'filename': filename,
        'approaches': {},
        'fallback': None
    }
    
    logger.info(f"\n{'='*60}")
    logger.info(f"EVALUATING: {filename}")
    logger.info(f"{'='*60}")
    
    # Generate fallback (first sentence method)
    first_desc = next(iter(descriptions.values()))['description']
    fallback = extract_first_sentence_fallback(first_desc)
    results['fallback'] = fallback
    logger.info(f"FALLBACK (First Sentence): {fallback}")
    
    # Try original AI + Claude Haiku for each configuration
    for config_key, desc_data in descriptions.items():
        provider = desc_data['provider']
        model = desc_data['model']
        prompt_style = desc_data['prompt']
        description = desc_data['description']
        
        logger.info(f"\n--- Configuration: {provider} {model} {prompt_style} ---")
        logger.info(f"Original description length: {len(description)} characters, {len(description.split())} words")
        logger.info(f"Workflow: {desc_data['workflow_dir']}")
        
        approach_results = {
            'provider': provider,
            'model': model,
            'prompt_style': prompt_style,
            'original_description_length': len(description),
            'original_description_words': len(description.split()),
            'workflow_dir': desc_data['workflow_dir'],
            'original_ai_alt_text': None,
            'claude_haiku_alt_text': None
        }
        
        # Create prompt for alt text generation
        alt_prompt = create_alt_text_prompt(description)
        
        # 1. Try original AI (if not Ollama)
        if provider == 'claude':
            logger.info("Generating alt text with original AI (Claude)...")
            original_alt = call_claude_api(claude_api_key, alt_prompt, model)
            approach_results['original_ai_alt_text'] = original_alt
            if original_alt:
                logger.info(f"ORIGINAL AI (Claude {model}): {original_alt}")
                logger.info(f"Length: {len(original_alt.split())} words")
            else:
                logger.error("Failed to generate alt text with original Claude model")
                
        elif provider == 'openai':
            openai_key = os.getenv('OPENAI_API_KEY')
            if openai_key:
                logger.info("Generating alt text with original AI (OpenAI)...")
                original_alt = call_openai_api(openai_key, alt_prompt, model)
                approach_results['original_ai_alt_text'] = original_alt
                if original_alt:
                    logger.info(f"ORIGINAL AI (OpenAI {model}): {original_alt}")
                    logger.info(f"Length: {len(original_alt.split())} words")
                else:
                    logger.error("Failed to generate alt text with original OpenAI model")
            else:
                logger.warning("OPENAI_API_KEY not set, skipping original AI alt text generation")
                approach_results['original_ai_alt_text'] = "SKIPPED: No OpenAI API key"
                
        else:  # Ollama
            logger.info("Skipping original AI for Ollama (would require local setup)")
            approach_results['original_ai_alt_text'] = "SKIPPED: Ollama requires local setup"
        
        # 2. Always try Claude Haiku for comparison
        logger.info("Generating alt text with Claude Haiku 3.5...")
        claude_alt = call_claude_api(claude_api_key, alt_prompt, "claude-3-5-haiku-20241022")
        approach_results['claude_haiku_alt_text'] = claude_alt
        if claude_alt:
            logger.info(f"CLAUDE HAIKU: {claude_alt}")
            logger.info(f"Length: {len(claude_alt.split())} words")
        else:
            logger.error("Failed to generate alt text with Claude Haiku")
        
        results['approaches'][config_key] = approach_results
        
        # Small delay between API calls
        time.sleep(1)
    
    return results


def generate_summary_report(all_results: List[Dict], output_dir: Path) -> Path:
    """Generate a summary report of all results."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = output_dir / f'alt_text_evaluation_summary_{timestamp}.txt'
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("Alt Text Generation Evaluation Summary\n")
        f.write("="*50 + "\n\n")
        
        for result in all_results:
            f.write(f"IMAGE: {result['filename']}\n")
            f.write("-" * 40 + "\n")
            
            f.write(f"FALLBACK (First Sentence): {result['fallback']}\n\n")
            
            for config_key, approach in result['approaches'].items():
                f.write(f"Configuration: {approach['provider']} {approach['model']} {approach['prompt_style']}\n")
                f.write(f"Workflow: {approach['workflow_dir']}\n")
                f.write(f"Original description: {approach['original_description_words']} words\n")
                
                if approach['original_ai_alt_text']:
                    f.write(f"Original AI: {approach['original_ai_alt_text']}\n")
                    if not approach['original_ai_alt_text'].startswith('SKIPPED'):
                        f.write(f"  ({len(approach['original_ai_alt_text'].split())} words)\n")
                
                if approach['claude_haiku_alt_text']:
                    f.write(f"Claude Haiku: {approach['claude_haiku_alt_text']}\n")
                    f.write(f"  ({len(approach['claude_haiku_alt_text'].split())} words)\n")
                
                f.write("\n")
            
            f.write("\n" + "="*50 + "\n\n")
    
    return report_file


def main():
    parser = argparse.ArgumentParser(description='Evaluate alt text generation approaches')
    parser.add_argument('--descriptions-dir', type=Path, 
                       default=Path('Descriptions'),
                       help='Directory containing workflow descriptions')
    parser.add_argument('--output-dir', type=Path,
                       default=Path('jsondata'),
                       help='Directory to write evaluation results')
    parser.add_argument('--count', type=int, default=5,
                       help='Number of images to evaluate')
    
    args = parser.parse_args()
    
    # Ensure output directory exists
    args.output_dir.mkdir(exist_ok=True)
    
    # Set up logging
    logger = setup_logging(args.output_dir)
    
    logger.info("="*70)
    logger.info("Alt Text Generation Evaluation")
    logger.info("="*70)
    logger.info(f"Descriptions directory: {args.descriptions_dir}")
    logger.info(f"Output directory: {args.output_dir}")
    logger.info(f"Images to evaluate: {args.count}")
    logger.info("")
    
    # Check for Claude API key
    claude_api_key = get_claude_api_key()
    if not claude_api_key:
        return 1
    
    logger.info("Claude API key found ✓")
    
    # Check for OpenAI API key (optional)
    openai_key = os.getenv('OPENAI_API_KEY')
    if openai_key:
        logger.info("OpenAI API key found ✓")
    else:
        logger.info("OpenAI API key not found - will skip OpenAI original AI generation")
    
    # Find random images
    logger.info(f"\nSearching for images with descriptions...")
    selected_images = find_random_images_with_descriptions(args.descriptions_dir, args.count)
    
    if not selected_images:
        logger.error("No suitable images found for evaluation")
        return 1
    
    # Generate alt text for each image
    all_results = []
    for i, (filename, descriptions) in enumerate(selected_images, 1):
        logger.info(f"\nProcessing image {i}/{len(selected_images)}")
        
        try:
            result = generate_alt_text_for_image(filename, descriptions, claude_api_key)
            all_results.append(result)
        except Exception as e:
            logger.error(f"Error processing {filename}: {e}")
            continue
    
    # Generate summary report
    if all_results:
        report_file = generate_summary_report(all_results, args.output_dir)
        logger.info(f"\n{'='*70}")
        logger.info("EVALUATION COMPLETE!")
        logger.info(f"{'='*70}")
        logger.info(f"Summary report: {report_file}")
        logger.info(f"Detailed log available in the log file")
        logger.info(f"Images evaluated: {len(all_results)}")
        logger.info(f"Total configurations tested: {sum(len(r['approaches']) for r in all_results)}")
    else:
        logger.error("No results generated")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())