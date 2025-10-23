#!/usr/bin/env python3
"""
Generate descriptions JSON files from IDT workflow directories.

This script scans workflow directories for description files and extracts
descriptions into JSON format for the web gallery to consume.

The script is designed to be flexible and handle growing datasets:
- Scans for workflows matching a pattern (e.g., "25imagetest")
- Extracts provider, model, and prompt style from directory names
- Groups descriptions by configuration
- Generates index.json with available configurations
- Creates individual JSON files for each provider/model/prompt combination

Usage:
    python generate_descriptions.py [--descriptions-dir PATH] [--output-dir PATH] [--pattern PATTERN]
"""

import os
import sys
import json
import re
import argparse
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Optional


def parse_workflow_directory(dir_name: str) -> Optional[Tuple[str, str, str, str]]:
    """
    Parse workflow directory name to extract components.
    
    Format: wf_WORKFLOWNAME_PROVIDER_MODEL_[VARIANT_]PROMPTSTYLE_TIMESTAMP
    
    Returns:
        Tuple of (workflow_name, provider, model, prompt_style) or None if parse fails
    """
    # Remove wf_ prefix
    if not dir_name.startswith('wf_'):
        return None
    
    parts = dir_name[3:].split('_')
    
    if len(parts) < 5:
        return None
    
    workflow_name = parts[0]
    provider = parts[1]
    
    # Find timestamp - it's the last TWO parts (YYYYMMDD_HHMMSS)
    # Both should be numeric (digits only)
    if len(parts) < 2:
        return None
    
    # Check if last two parts form a valid timestamp
    if (parts[-2].isdigit() and len(parts[-2]) == 8 and  # Date: YYYYMMDD
        parts[-1].isdigit() and len(parts[-1]) == 6):    # Time: HHMMSS
        timestamp_idx = len(parts) - 2  # Index of date part
    else:
        return None
    
    if timestamp_idx < 4:
        return None
    
    # Prompt style is before timestamp (before date part)
    prompt_style = parts[timestamp_idx - 1]
    
    # Model is everything between provider and prompt_style
    model_parts = parts[2:timestamp_idx - 1]
    model = '_'.join(model_parts)
    
    return (workflow_name, provider, model, prompt_style)


def extract_descriptions(desc_file: Path) -> Dict[str, Dict[str, str]]:
    """
    Extract descriptions from a workflow's description file.
    
    Returns:
        Dictionary mapping image filenames to description data
    """
    descriptions = {}
    
    try:
        with open(desc_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split by separator lines
        blocks = re.split(r'\n-{40,}\n', content)
        
        for block in blocks:
            if not block.strip():
                continue
            
            # Extract fields using regex
            file_match = re.search(r'^File:\s*(.+?)$', block, re.MULTILINE)
            provider_match = re.search(r'^Provider:\s*(.+?)$', block, re.MULTILINE)
            model_match = re.search(r'^Model:\s*(.+?)$', block, re.MULTILINE)
            prompt_match = re.search(r'^Prompt Style:\s*(.+?)$', block, re.MULTILINE)
            timestamp_match = re.search(r'^Timestamp:\s*(.+?)$', block, re.MULTILINE)
            
            # Extract description (everything after "Description: " up to "Timestamp:")
            # Description can start on same line or next line
            desc_match = re.search(r'Description:\s*(.*?)\s*Timestamp:', block, re.DOTALL)
            
            if file_match and desc_match:
                file_path = file_match.group(1).strip()
                description = desc_match.group(1).strip()
                
                # Extract just the filename from path
                filename = os.path.basename(file_path)
                
                descriptions[filename] = {
                    'description': description,
                    'provider': provider_match.group(1).strip() if provider_match else '',
                    'model': model_match.group(1).strip() if model_match else '',
                    'prompt_style': prompt_match.group(1).strip() if prompt_match else '',
                    'timestamp': timestamp_match.group(1).strip() if timestamp_match else ''
                }
    
    except Exception as e:
        print(f"Error processing {desc_file}: {e}")
    
    return descriptions


def scan_workflows(descriptions_dir: Path, pattern: str) -> Dict[str, Dict[str, Dict[str, str]]]:
    """
    Scan workflow directories and extract all descriptions.
    
    Returns:
        Nested dict: {provider: {model: {prompt_style: {image: desc_data}}}}
    """
    all_data = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    
    print(f"Scanning {descriptions_dir} for workflows matching pattern: {pattern}")
    
    if not descriptions_dir.exists():
        print(f"Error: Directory {descriptions_dir} does not exist")
        return {}
    
    workflow_dirs = [d for d in descriptions_dir.iterdir() if d.is_dir() and pattern.lower() in d.name.lower()]
    
    print(f"Found {len(workflow_dirs)} workflow directories")
    
    for workflow_dir in workflow_dirs:
        print(f"Processing: {workflow_dir.name}")
        
        # Find description file
        desc_file = workflow_dir / 'descriptions' / 'image_descriptions.txt'
        if not desc_file.exists():
            print(f"  Skipping: No descriptions file found")
            continue
        
        # Extract descriptions
        descriptions = extract_descriptions(desc_file)
        print(f"  Found {len(descriptions)} image descriptions")
        
        if not descriptions:
            print(f"  Skipping: No valid descriptions extracted")
            continue
        
        # Get provider, model, and prompt from the actual description data (not directory name)
        # All images should have the same provider/model/prompt, so use first one
        first_desc = next(iter(descriptions.values()))
        provider = first_desc.get('provider', '')
        model = first_desc.get('model', '')
        prompt_style = first_desc.get('prompt_style', '')
        
        if not provider or not model or not prompt_style:
            print(f"  Skipping: Missing provider/model/prompt in description data")
            continue
        
        # Normalize model names: treat "model" and "model:latest" as the same
        # This prevents duplicates like moondream and moondream:latest
        if provider == 'ollama' and ':' not in model:
            model = f"{model}:latest"
            print(f"  Normalized model name to: {model}")
            
        print(f"  Using: provider={provider}, model={model}, prompt={prompt_style}")
        
        # Store in nested structure
        # If we already have data for this config, merge (keep existing if duplicate)
        existing = all_data[provider][model][prompt_style]
        if existing:
            print(f"  Merging with existing data for this configuration")
            existing.update(descriptions)
        else:
            all_data[provider][model][prompt_style] = descriptions
    
    return all_data


def generate_config_index(data: Dict) -> Dict:
    """
    Generate configuration index from data.
    
    Returns:
        Dict with providers, models, and prompts structure
    """
    config = {
        'providers': list(data.keys()),
        'models': {},
        'prompts': {}
    }
    
    for provider, models in data.items():
        config['models'][provider] = list(models.keys())
        config['prompts'][provider] = {}
        
        for model, prompts in models.items():
            config['prompts'][provider][model] = list(prompts.keys())
    
    return config


def write_output_files(data: Dict, output_dir: Path):
    """
    Write JSON files for the gallery to consume.
    
    Creates:
    - index.json: Configuration index with available providers/models/prompts
    - {provider}_{model}_{prompt}.json: Individual description files
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate and write index
    config = generate_config_index(data)
    from datetime import datetime
    index_data = {
        'configs': config,
        'generated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_configurations': sum(
            len(prompts) 
            for models in data.values() 
            for prompts in models.values()
        )
    }
    
    index_file = output_dir / 'index.json'
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, indent=2)
    print(f"\nWrote index: {index_file}")
    
    # Write individual description files
    count = 0
    for provider, models in data.items():
        for model, prompts in models.items():
            for prompt_style, images in prompts.items():
                # Sanitize filename
                safe_provider = provider.replace(':', '_').replace('/', '_')
                safe_model = model.replace(':', '_').replace('/', '_')
                safe_prompt = prompt_style.replace(':', '_').replace('/', '_')
                
                filename = f"{safe_provider}_{safe_model}_{safe_prompt}.json"
                filepath = output_dir / filename
                
                file_data = {
                    'provider': provider,
                    'model': model,
                    'prompt_style': prompt_style,
                    'images': images
                }
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(file_data, f, indent=2)
                
                count += 1
                print(f"Wrote: {filename} ({len(images)} images)")
    
    print(f"\nTotal: {count} description files generated")
    print(f"Output directory: {output_dir}")


def main():
    parser = argparse.ArgumentParser(
        description='Generate JSON description files from IDT workflows for web gallery'
    )
    parser.add_argument(
        '--input-dir',
        '--descriptions-dir',
        dest='descriptions_dir',
        type=Path,
        default=Path('c:/idt/Descriptions'),
        help='Path to Descriptions directory containing workflow subdirectories (default: c:/idt/Descriptions)'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('descriptions'),
        help='Output directory for JSON files (default: descriptions)'
    )
    parser.add_argument(
        '--name',
        '--pattern',
        dest='pattern',
        type=str,
        default='25imagetest',
        help='Workflow name pattern to match in directory names (default: 25imagetest)'
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("IDT Gallery Description Generator")
    print("=" * 70)
    
    # Scan and extract
    data = scan_workflows(args.descriptions_dir, args.pattern)
    
    if not data:
        print("\nNo data found! Check your descriptions directory and pattern.")
        return 1
    
    # Write output
    write_output_files(data, args.output_dir)
    
    print("\n" + "=" * 70)
    print("Generation complete!")
    print("=" * 70)
    print("\nNext steps:")
    print("1. Copy the descriptions/ directory to your web server")
    print("2. Copy index.html to your web server")
    print("3. Copy your 25 JPG images to your web server")
    print("4. Open index.html in a browser to test")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
