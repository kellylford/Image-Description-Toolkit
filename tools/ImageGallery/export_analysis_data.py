#!/usr/bin/env python3
"""
Export Image Gallery Analysis Data to CSV

This script extracts comprehensive data from IDT workflow directories and log files
to create a flat CSV file with one record per image processed. Includes timing,
token usage, costs, and all metadata for analysis.

Usage:
    python export_analysis_data.py [--descriptions-dir PATH] [--output-dir PATH] [--pattern PATTERN]
"""

import os
import sys
import csv
import re
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import json
# Cost estimates per million tokens (approximate, varies by provider)
COST_PER_MILLION_TOKENS = {
    'claude': {
        'claude-3-5-haiku-20241022': {'input': 0.25, 'output': 1.25},
        'claude-opus-4-20250514': {'input': 15.00, 'output': 75.00},
        'claude-sonnet-4-5-20250929': {'input': 3.00, 'output': 15.00},
    },
    'openai': {
        'gpt-4o': {'input': 2.50, 'output': 10.00},
        'gpt-4o-mini': {'input': 0.15, 'output': 0.60},
    },
    'ollama': {
        # Ollama is typically free/local, but we'll track tokens
        'default': {'input': 0.00, 'output': 0.00}
    }
}


def parse_workflow_directory(dir_name: str) -> Optional[Tuple[str, str, str, str, str]]:
    """
    Parse workflow directory name to extract components.
    
    Returns:
        Tuple of (workflow_name, provider, model, prompt_style, timestamp) or None
    """
    if not dir_name.startswith('wf_'):
        return None
    
    parts = dir_name[3:].split('_')
    
    if len(parts) < 5:
        return None
    
    workflow_name = parts[0]
    provider = parts[1]
    
    # Find timestamp - last TWO parts (YYYYMMDD_HHMMSS)
    if (len(parts) >= 2 and parts[-2].isdigit() and len(parts[-2]) == 8 and  
        parts[-1].isdigit() and len(parts[-1]) == 6):
        timestamp_idx = len(parts) - 2
        timestamp = f"{parts[-2]}_{parts[-1]}"
    else:
        return None
    
    if timestamp_idx < 4:
        return None
    
    prompt_style = parts[timestamp_idx - 1]
    model_parts = parts[2:timestamp_idx - 1]
    model = '_'.join(model_parts)
    
    return (workflow_name, provider, model, prompt_style, timestamp)


def parse_log_file(log_file: Path) -> Dict[str, Dict]:
    """
    Parse image_describer log file to extract per-image timing and token data.
    
    Returns:
        Dictionary mapping image filenames to timing/token data
    """
    image_data = {}
    
    if not log_file.exists():
        return image_data
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse image processing data line by line for more reliable extraction
        lines = content.split('\n')
        current_image = {}
        
        for i, line in enumerate(lines):
            # Look for image processing start
            if 'Describing image' in line and 'of' in line:
                match = re.search(r'Describing image (\d+) of (\d+): ([^\s]+)', line)
                if match:
                    # Save previous image if we have one
                    if current_image and 'filename' in current_image:
                        filename = os.path.basename(current_image['filename'].strip())
                        image_data[filename] = current_image
                    
                    # Start new image
                    current_image = {
                        'image_number': int(match.group(1)),
                        'total_images': int(match.group(2)),
                        'filename': match.group(3).strip()
                    }
            
            # Look for timing and token data
            elif 'Start time:' in line:
                match = re.search(r'Start time: ([^-]+)', line)
                if match and current_image:
                    current_image['start_time'] = match.group(1).strip()
            
            elif 'End time:' in line:
                match = re.search(r'End time: ([^-]+)', line)
                if match and current_image:
                    current_image['end_time'] = match.group(1).strip()
            
            elif 'Processing duration:' in line:
                match = re.search(r'Processing duration: ([\d.]+) seconds', line)
                if match and current_image:
                    current_image['processing_duration'] = float(match.group(1))
            
            elif 'Token usage:' in line:
                match = re.search(r'Token usage: (\d+) total \((\d+) prompt \+ (\d+) completion\)', line)
                if match and current_image:
                    current_image['total_tokens'] = int(match.group(1))
                    current_image['prompt_tokens'] = int(match.group(2))
                    current_image['completion_tokens'] = int(match.group(3))
        
        # Don't forget the last image
        if current_image and 'filename' in current_image:
            filename = os.path.basename(current_image['filename'].strip())
            image_data[filename] = current_image
    
    except Exception as e:
        print(f"Error parsing log file {log_file}: {e}")
    
    return image_data


def calculate_cost(provider: str, model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Calculate estimated cost based on token usage."""
    
    # Get cost structure for provider/model
    if provider in COST_PER_MILLION_TOKENS:
        if model in COST_PER_MILLION_TOKENS[provider]:
            costs = COST_PER_MILLION_TOKENS[provider][model]
        else:
            # Use default for provider if specific model not found
            if provider == 'ollama':
                costs = COST_PER_MILLION_TOKENS['ollama']['default']
            else:
                return 0.0
    else:
        return 0.0
    
    # Calculate cost (rates are per million tokens)
    input_cost = (prompt_tokens / 1_000_000) * costs['input']
    output_cost = (completion_tokens / 1_000_000) * costs['output']
    
    return input_cost + output_cost


def extract_descriptions(desc_file: Path) -> Dict[str, Dict]:
    """Extract descriptions and metadata from description file."""
    descriptions = {}
    
    try:
        with open(desc_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split by separator lines
        blocks = re.split(r'\n-{40,}\n', content)
        
        for block in blocks:
            if not block.strip():
                continue
            
            # Extract fields
            file_match = re.search(r'^File:\s*(.+?)$', block, re.MULTILINE)
            provider_match = re.search(r'^Provider:\s*(.+?)$', block, re.MULTILINE)
            model_match = re.search(r'^Model:\s*(.+?)$', block, re.MULTILINE)
            prompt_match = re.search(r'^Prompt Style:\s*(.+?)$', block, re.MULTILINE)
            timestamp_match = re.search(r'^Timestamp:\s*(.+?)$', block, re.MULTILINE)
            photo_date_match = re.search(r'^Photo Date:\s*(.+?)$', block, re.MULTILINE)
            camera_match = re.search(r'^Camera:\s*(.+?)$', block, re.MULTILINE)
            
            # Extract description
            desc_match = re.search(r'Description:\s*(.*?)\s*Timestamp:', block, re.DOTALL)
            
            if file_match and desc_match:
                filename = os.path.basename(file_match.group(1).strip())
                
                descriptions[filename] = {
                    'description': desc_match.group(1).strip(),
                    'provider': provider_match.group(1).strip() if provider_match else '',
                    'model': model_match.group(1).strip() if model_match else '',
                    'prompt_style': prompt_match.group(1).strip() if prompt_match else '',
                    'timestamp': timestamp_match.group(1).strip() if timestamp_match else '',
                    'photo_date': photo_date_match.group(1).strip() if photo_date_match else '',
                    'camera': camera_match.group(1).strip() if camera_match else '',
                }
    
    except Exception as e:
        print(f"Error processing {desc_file}: {e}")
    
    return descriptions


def get_alt_text_from_json(provider: str, model: str, prompt_style: str, image_filename: str, jsondata_dir: Path) -> str:
    """Extract alt text from JSON file if available."""
    try:
        # Build JSON filename (convert colons to underscores for filesystem compatibility)
        safe_model = model.replace(':', '_')
        json_filename = f"{provider}_{safe_model}_{prompt_style}.json"
        json_file = jsondata_dir / json_filename
        
        if not json_file.exists():
            return ''
        
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Get alt text for this specific image
        if 'images' in data and image_filename in data['images']:
            image_data = data['images'][image_filename]
            return image_data.get('alt_text', '')
        
        return ''
    except Exception as e:
        print(f"  Warning: Could not extract alt text from {json_filename}: {e}")
        return ''


def scan_and_export(descriptions_dir: Path, pattern: str, output_file: Path):
    """
    Scan workflow directories and export comprehensive CSV data.
    """
    print(f"Scanning {descriptions_dir} for workflows matching pattern: {pattern}")
    
    if not descriptions_dir.exists():
        print(f"Error: Directory {descriptions_dir} does not exist")
        return
    
    # Look for jsondata directory (for alt text)
    jsondata_dir = descriptions_dir.parent / 'jsondata'
    if jsondata_dir.exists():
        print(f"Alt text source: {jsondata_dir}")
    else:
        print(f"Warning: No jsondata directory found at {jsondata_dir} - alt text will be empty")
    
    workflow_dirs = [d for d in descriptions_dir.iterdir() 
                    if d.is_dir() and pattern.lower() in d.name.lower()]
    
    print(f"Found {len(workflow_dirs)} workflow directories")
    
    # Prepare CSV data
    csv_data = []
    
    for workflow_dir in workflow_dirs:
        print(f"Processing: {workflow_dir.name}")
        
        # Parse directory name
        parsed = parse_workflow_directory(workflow_dir.name)
        if not parsed:
            print(f"  Skipping: Could not parse directory name")
            continue
        
        workflow_name, provider, model, prompt_style, timestamp = parsed
        
        # Find description file
        desc_file = workflow_dir / 'descriptions' / 'image_descriptions.txt'
        if not desc_file.exists():
            print(f"  Skipping: No descriptions file found")
            continue
        
        # Find log file (look for image_describer_*.log)
        log_files = list((workflow_dir / 'logs').glob('image_describer_*.log'))
        log_data = {}
        if log_files:
            log_data = parse_log_file(log_files[0])
            print(f"  Found timing data for {len(log_data)} images")
        else:
            print(f"  No log file found")
        
        # Extract descriptions
        descriptions = extract_descriptions(desc_file)
        print(f"  Found {len(descriptions)} image descriptions")
        
        # Combine data for each image
        for filename, desc_data in descriptions.items():
            timing_data = log_data.get(filename, {})
            
            # Calculate estimated cost
            prompt_tokens = timing_data.get('prompt_tokens', 0)
            completion_tokens = timing_data.get('completion_tokens', 0)
            estimated_cost = calculate_cost(provider, model, prompt_tokens, completion_tokens)
            
            # Extract alt text from JSON file if available
            alt_text = get_alt_text_from_json(provider, model, prompt_style, filename, jsondata_dir) if jsondata_dir.exists() else ''
            
            # Build comprehensive record
            record = {
                'workflow_name': workflow_name,
                'workflow_timestamp': timestamp,
                'provider': provider,
                'model': model,
                'prompt_style': prompt_style,
                'image_filename': filename,
                'image_number': timing_data.get('image_number', ''),
                'total_images_in_run': timing_data.get('total_images', ''),
                'processing_duration_seconds': timing_data.get('processing_duration', ''),
                'start_time': timing_data.get('start_time', ''),
                'end_time': timing_data.get('end_time', ''),
                'total_tokens': timing_data.get('total_tokens', ''),
                'prompt_tokens': prompt_tokens,
                'completion_tokens': completion_tokens,
                'estimated_cost_usd': round(estimated_cost, 6) if estimated_cost > 0 else '',
                'photo_date': desc_data.get('photo_date', ''),
                'camera': desc_data.get('camera', ''),
                'description_timestamp': desc_data.get('timestamp', ''),
                'description_length': len(desc_data.get('description', '')),
                'description': desc_data.get('description', '').replace('\n', ' ').replace('\r', ''),
                'alt_text': alt_text.replace('\n', ' ').replace('\r', '') if alt_text else ''
            }
            
            csv_data.append(record)
    
    # Write CSV file
    if csv_data:
        fieldnames = csv_data[0].keys()
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_data)
        
        print(f"\n{'='*70}")
        print(f"CSV Export Complete!")
        print(f"{'='*70}")
        print(f"Output file: {output_file}")
        print(f"Total records: {len(csv_data)}")
        print(f"Unique workflows: {len(set(r['workflow_timestamp'] for r in csv_data))}")
        print(f"Providers: {', '.join(sorted(set(r['provider'] for r in csv_data)))}")
        print(f"Models: {len(set(r['model'] for r in csv_data))}")
        print(f"Prompt styles: {', '.join(sorted(set(r['prompt_style'] for r in csv_data)))}")
        
        # Summary statistics
        total_duration = sum(float(r['processing_duration_seconds']) for r in csv_data if r['processing_duration_seconds'])
        total_tokens = sum(int(r['total_tokens']) for r in csv_data if r['total_tokens'])
        total_cost = sum(float(r['estimated_cost_usd']) for r in csv_data if r['estimated_cost_usd'])
        
        print(f"\nSummary Statistics:")
        print(f"Total processing time: {total_duration:.1f} seconds ({total_duration/60:.1f} minutes)")
        print(f"Total tokens used: {total_tokens:,}")
        print(f"Estimated total cost: ${total_cost:.4f}")
        print(f"Average seconds per image: {total_duration/len(csv_data):.2f}")
        print(f"{'='*70}")
    else:
        print("No data found to export")


def main():
    parser = argparse.ArgumentParser(description='Export image gallery analysis data to CSV')
    parser.add_argument('--descriptions-dir', type=Path, 
                       default=Path('Descriptions'),
                       help='ONLY source: relative Descriptions directory')
    parser.add_argument('--output-dir', type=Path,
                       default=Path('jsondata'),
                       help='Directory to write CSV file')
    parser.add_argument('--pattern', type=str, default='25imagetest',
                       help='Pattern to match workflow directories')
    
    args = parser.parse_args()
    
    # Ensure output directory exists
    args.output_dir.mkdir(exist_ok=True)
    
    # Generate timestamp for output file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = args.output_dir / f'image_analysis_data_{timestamp}.csv'
    
    print("="*70)
    print("Image Gallery Analysis Data Export")
    print("="*70)
    print(f"SOURCE OF TRUTH: {args.descriptions_dir} (relative directory ONLY)")
    print(f"Output file: {output_file}")
    print(f"Workflow pattern: {args.pattern}")  
    print("")
    print("NOTE: Only data in the relative Descriptions directory will be processed.")
    print("If workflow data is missing, copy it here first.")
    print("")
    
    scan_and_export(args.descriptions_dir, args.pattern, output_file)


if __name__ == '__main__':
    main()