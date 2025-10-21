#!/usr/bin/env python3
"""
Combine descriptions from multiple workflow directories into a single CSV file.

This script reads the image_descriptions.txt files from all workflow directories
and creates a CSV with columns: Image Name, Description1, Description2, etc.

Formats:
  - CSV (default): Standard comma-delimited with quoted fields - opens directly in Excel
  - TSV: Tab-delimited - opens directly in Excel, good for long text fields
  - ATSV: @-delimited (legacy) - requires Excel import wizard, but still supported
"""

import argparse
import csv
import sys
from pathlib import Path

# Add parent directory to path for resource manager import
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

try:
    from scripts.resource_manager import get_resource_path
except ImportError:
    # Fallback if resource manager not available
    def get_resource_path(relative_path):
        return Path(__file__).parent.parent / relative_path
import re
import os
from pathlib import Path
from typing import Dict, List, Tuple
from collections import OrderedDict
from datetime import datetime
from analysis_utils import get_safe_filename, ensure_directory


def get_image_date_for_sorting(image_name: str, base_dir: Path) -> datetime:
    """
    Extract the date/time the image was taken from EXIF data for sorting purposes.
    
    Searches for the image file in the workflow directories and tries multiple EXIF fields:
    1. DateTimeOriginal (when photo was taken)
    2. DateTimeDigitized (when photo was digitized) 
    3. DateTime (file modification date in EXIF)
    4. Falls back to file modification time
    
    Args:
        image_name: The filename to search for
        base_dir: Base directory containing workflow folders
        
    Returns:
        datetime object for sorting (earliest possible date if file not found)
    """
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS
        
        # Search for the image file in workflow directories
        image_path = None
        for workflow_dir in base_dir.glob("wf_*"):
            # Check common subdirectories where images might be
            for subdir in ['converted_images', 'extracted_frames', '']:
                if subdir:
                    search_dir = workflow_dir / subdir
                else:
                    search_dir = workflow_dir
                    
                if search_dir.exists():
                    # Look for the exact filename
                    potential_path = search_dir / image_name
                    if potential_path.exists():
                        image_path = potential_path
                        break
                    
                    # Also check subdirectories (for video frames)
                    for img_file in search_dir.rglob(image_name):
                        if img_file.is_file():
                            image_path = img_file
                            break
                            
                if image_path:
                    break
            if image_path:
                break
        
        if not image_path or not image_path.exists():
            # Return epoch time if file not found (will sort to beginning)
            return datetime.fromtimestamp(0)
        
        # Try to extract EXIF date
        with Image.open(image_path) as img:
            exif_data = img.getexif()
            
            if exif_data:
                # Convert to human-readable tags
                exif_dict = {}
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)
                    exif_dict[tag] = value
                
                # Try different datetime fields in priority order
                datetime_fields = ['DateTimeOriginal', 'DateTimeDigitized', 'DateTime']
                
                for field in datetime_fields:
                    if field in exif_dict:
                        dt_str = exif_dict[field]
                        if dt_str:
                            try:
                                # Parse EXIF datetime format: YYYY:MM:DD HH:MM:SS
                                return datetime.strptime(str(dt_str), '%Y:%m:%d %H:%M:%S')
                            except (ValueError, TypeError):
                                continue
        
        # Fallback to file modification time if no EXIF date found
        file_mtime = os.path.getmtime(image_path)
        return datetime.fromtimestamp(file_mtime)
        
    except Exception as e:
        # Return epoch time if any error occurs (will sort to beginning)
        return datetime.fromtimestamp(0)


def parse_description_file(file_path: Path) -> OrderedDict:
    """
    Parse a workflow description file and extract image paths and descriptions.
    
    Args:
        file_path: Path to the image_descriptions.txt file
    
    Returns:
        OrderedDict mapping normalized image names to descriptions (in processing order)
    """
    descriptions = OrderedDict()
    
    if not file_path.exists():
        print(f"Warning: {file_path} not found")
        return descriptions
    
    current_file = None
    current_description = []
    in_description = False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            # Check for file marker - this starts a new image block
            if line.startswith("File: "):
                # Save previous description if exists
                if current_file and current_description:
                    desc_text = ' '.join(current_description).strip()
                    # Clean up multiple consecutive spaces
                    desc_text = ' '.join(desc_text.split())
                    descriptions[current_file] = desc_text
                    current_description = []
                
                # Extract file path and normalize to just the image name
                file_path_str = line[6:].strip()  # Remove "File: " prefix
                # Extract just the filename from paths like "converted_images\IMG_3136.jpg"
                # or "extracted_frames\IMG_3136\IMG_3136_0.00s.jpg" or "09\IMG_3137.PNG"
                current_file = Path(file_path_str).name
                in_description = False
                
            # Check for description marker - this starts the description content
            elif line.startswith("Description: "):
                desc_text = line[13:].strip()  # Remove "Description: " prefix
                if desc_text:  # Only add if not empty
                    current_description.append(desc_text)
                in_description = True
                
            # Skip metadata lines (Provider, Model, Prompt Style) if we haven't started description yet
            elif not in_description and (line.startswith("Provider: ") or 
                                        line.startswith("Model: ") or 
                                        line.startswith("Prompt Style: ")):
                # These are metadata lines, skip them
                continue
                
            # Once we've started a description, capture everything until the next "File:" marker
            # This includes lines that start with "---" (markdown separators within descriptions)
            elif in_description and current_file:
                # Skip "---" lines that are just markdown separators
                if line.strip() == "---" or line.strip().startswith("---"):
                    # Don't add markdown separators to the description
                    continue
                # Keep empty lines to preserve paragraph breaks
                elif line.strip():
                    current_description.append(line.strip())
                else:
                    # Empty line - add a space to separate paragraphs
                    current_description.append(' ')
        
        # Save last description if file doesn't end with separator
        if current_file and current_description:
            # Join and clean up extra spaces
            desc_text = ' '.join(current_description).strip()
            # Clean up multiple consecutive spaces
            desc_text = ' '.join(desc_text.split())
            descriptions[current_file] = desc_text
    
    print(f"Parsed {len(descriptions)} descriptions from {file_path.parent.parent.name}")
    return descriptions


def get_workflow_name(workflow_dir: Path) -> str:
    """
    Get the workflow name from workflow_metadata.json if it exists.
    Falls back to directory name parsing if no metadata file found.
    
    Args:
        workflow_dir: Path to the workflow directory
        
    Returns:
        Workflow name string (or None if not available)
    """
    import json
    
    metadata_file = workflow_dir / "workflow_metadata.json"
    
    if metadata_file.exists():
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                return metadata.get('workflow_name')
        except Exception as e:
            print(f"Warning: Could not read metadata from {metadata_file}: {e}")
    
    # No metadata file - workflows created before the naming feature
    # Return None to indicate no workflow name available
    return None


def get_workflow_label(workflow_dir: Path) -> Tuple[str, str]:
    """
    Extract a readable label and prompt style from the workflow directory name.
    Creates unique, distinguishable labels for all models.
    
    Returns:
        Tuple of (model_label, prompt_style)
    
    Examples:
        wf_claude_claude-3-haiku-20240307_narrative_... -> ("Claude Haiku 3", "narrative")
        wf_claude_claude-3-5-haiku-20241022_colorful_... -> ("Claude Haiku 3.5", "colorful")
        wf_ollama_llava_7b_artistic_... -> ("Ollama LLaVA 7B", "artistic")
        wf_ollama_llava_13b_narrative_... -> ("Ollama LLaVA 13B", "narrative")
        wf_openai_gpt-4o-mini_detailed_... -> ("OpenAI GPT-4o-mini", "detailed")
    """
    dir_name = workflow_dir.name
    
    # Extract provider and model from directory name
    # Format: wf_PROVIDER_MODEL_[VARIANT]_PROMPTSTYLE_DATETIME
    parts = dir_name.split('_')
    
    # Known prompt styles (must match those in image_describer_config.json)
    prompt_styles = ['narrative', 'detailed', 'concise', 'technical', 'creative', 'colorful', 'artistic', 'simple']
    
    # Find the prompt style (it's the part before the datetime)
    prompt_style = 'unknown'
    for i, part in enumerate(parts):
        if part.lower() in prompt_styles:
            prompt_style = part
            break
    
    if len(parts) >= 3:
        provider = parts[1].capitalize()
        model_part = parts[2]
        
        # Determine if there's a variant (between model and prompt style)
        # Check if parts[3] is NOT a prompt style and NOT a timestamp
        variant = None
        if len(parts) > 3 and parts[3].lower() not in prompt_styles and not parts[3].isdigit():
            variant = parts[3]
        
        # Create readable labels for Claude models
        model_label = None
        if provider.lower() == 'claude':
            # claude-3-haiku-20240307 -> Haiku 3
            # claude-3-5-haiku-20241022 -> Haiku 3.5
            # claude-opus-4-1-20250805 -> Opus 4.1
            # claude-sonnet-4-5-20250929 -> Sonnet 4.5
            if 'haiku' in model_part:
                if '3-5' in model_part:
                    model_label = "Claude Haiku 3.5"
                else:
                    model_label = "Claude Haiku 3"
            elif 'sonnet' in model_part:
                if '4-5' in model_part:
                    model_label = "Claude Sonnet 4.5"
                elif '3-7' in model_part:
                    model_label = "Claude Sonnet 3.7"
                elif 'sonnet-4' in model_part:
                    model_label = "Claude Sonnet 4"
                else:
                    model_label = "Claude Sonnet"
            elif 'opus' in model_part:
                if '4-1' in model_part:
                    model_label = "Claude Opus 4.1"
                elif 'opus-4-2' in model_part:
                    model_label = "Claude Opus 4"
                else:
                    model_label = "Claude Opus"
        
        # Create readable labels for Ollama models
        elif provider.lower() == 'ollama':
            # llava with variant (7b, 13b, 34b, latest)
            if 'llava' in model_part:
                base = "LLaVA"
                if 'phi3' in model_part:
                    base = "LLaVA-Phi3"
                elif 'llama3' in model_part:
                    base = "LLaVA-Llama3"
                
                # Format variant nicely
                if variant and variant != 'latest':
                    if variant.endswith('b'):  # 7b, 13b, 34b
                        model_label = f"Ollama {base} {variant.upper()}"
                    else:
                        model_label = f"Ollama {base} {variant}"
                else:
                    model_label = f"Ollama {base}"
            
            # llama3.2-vision with variant (11b, 90b, latest)
            elif 'llama3.2-vision' in model_part or 'llama3-2-vision' in model_part:
                if variant and variant != 'latest' and variant.endswith('b'):
                    model_label = f"Ollama Llama3.2-Vision {variant.upper()}"
                else:
                    model_label = "Ollama Llama3.2-Vision"
            
            # Other Ollama models (moondream, bakllava, etc.)
            elif model_part == 'moondream':
                model_label = "Ollama Moondream"
            elif model_part == 'bakllava':
                model_label = "Ollama BakLLaVA"
            elif 'minicpm' in model_part:
                if variant and variant.endswith('b'):
                    model_label = f"Ollama MiniCPM-V {variant.upper()}"
                else:
                    model_label = "Ollama MiniCPM-V"
            elif model_part == 'cogvlm2':
                model_label = "Ollama CogVLM2"
            elif model_part == 'internvl':
                model_label = "Ollama InternVL"
            elif 'mistral' in model_part:
                if 'small3.2' in model_part:
                    model_label = "Ollama Mistral 3.2"
                elif 'small3.1' in model_part:
                    model_label = "Ollama Mistral 3.1"
                else:
                    model_label = f"Ollama {model_part.title()}"
            elif 'qwen' in model_part:
                model_label = "Ollama Qwen 2.5 VL"
            else:
                # Generic fallback for Ollama
                if variant and variant != 'latest':
                    model_label = f"Ollama {model_part.title()} {variant}"
                else:
                    model_label = f"Ollama {model_part.title()}"
        
        # OpenAI models
        elif provider.lower() == 'openai':
            # gpt-4o, gpt-4o-mini, gpt-5
            if 'gpt-4o-mini' in model_part:
                model_label = "OpenAI GPT-4o-mini"
            elif 'gpt-4o' in model_part:
                model_label = "OpenAI GPT-4o"
            elif 'gpt-5' in model_part:
                model_label = "OpenAI GPT-5"
            else:
                model_label = f"OpenAI {model_part.upper()}"
        
        # Generic fallback for any other providers
        else:
            if variant and variant != 'latest':
                model_label = f"{provider} {model_part} {variant}"
            else:
                model_label = f"{provider} {model_part}"
        
        if model_label:
            return (model_label, prompt_style)
    
    return (dir_name, prompt_style)


def main():
    """Main function to combine workflow descriptions into CSV."""
    parser = argparse.ArgumentParser(
        description='Combine descriptions from multiple workflow directories into a single CSV file.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Create standard CSV sorted by date (default, opens directly in Excel)
  python combine_workflow_descriptions.py
  
  # Sort alphabetically by filename instead of by date
  python combine_workflow_descriptions.py --sort name
  
  # Create tab-separated file sorted by date
  python combine_workflow_descriptions.py --format tsv --output results.tsv
  
  # Use legacy @-separated format with alphabetical sorting
  python combine_workflow_descriptions.py --format atsv --sort name --output results.txt
  
  # Specify custom workflow directory with date sorting
  python combine_workflow_descriptions.py --input-dir /path/to/workflows --sort date
  
  # Use custom input, format, and sorting
  python combine_workflow_descriptions.py --input-dir /data/workflows --format tsv --sort name
        '''
    )
    
    parser.add_argument(
        '--input-dir',
        type=Path,
        default=None,
        help='Directory containing workflow folders (default: ../Descriptions relative to script)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='analysis/results/combineddescriptions.csv',
        help='Output filename (default: analysis/results/combineddescriptions.csv)'
    )
    
    parser.add_argument(
        '--format',
        type=str,
        choices=['csv', 'tsv', 'atsv'],
        default='csv',
        help='''Output format:
  csv  - Standard CSV with comma delimiter and quoted fields (recommended, opens directly in Excel)
  tsv  - Tab-separated values (good Excel compatibility, no quotes needed)
  atsv - @-separated values (legacy format, requires import wizard in Excel)
Default: csv'''
    )
    
    parser.add_argument(
        '--sort',
        type=str,
        choices=['name', 'date'],
        default='date',
        help='''Sort order for images:
  name - Sort alphabetically by filename (legacy behavior)
  date - Sort chronologically by image date (oldest to newest, using EXIF data when available)
Default: date'''
    )
    
    args = parser.parse_args()
    
    # Determine input directory
    if args.input_dir:
        base_dir = args.input_dir
    else:
        # Default to Descriptions directory in current working directory
        base_dir = Path.cwd() / "Descriptions"
    
    if not base_dir.exists():
        print(f"Error: Descriptions directory not found at: {base_dir}")
        print("\nPlease specify the correct directory with --input-dir")
        return 1
    
    workflow_dirs = sorted([d for d in base_dir.glob("wf_*") if d.is_dir()])
    
    if not workflow_dirs:
        print("No workflow directories found in Descriptions folder!")
        return
    
    print(f"Found {len(workflow_dirs)} workflow directories:")
    for wd in workflow_dirs:
        print(f"  - {wd.name}")
    print()
    
    # Parse all description files
    workflow_data = []  # List of (model_label, prompt_style, workflow_name, descriptions_dict)
    
    for workflow_dir in workflow_dirs:
        desc_file = workflow_dir / "descriptions" / "image_descriptions.txt"
        model_label, prompt_style = get_workflow_label(workflow_dir)
        workflow_name = get_workflow_name(workflow_dir)
        
        # Debug: Check if file exists
        if not desc_file.exists():
            print(f"  WARNING: Description file not found for {model_label} ({prompt_style})")
            print(f"      Expected: {desc_file}")
        
        descriptions = parse_description_file(desc_file)
        
        # Debug: Report parsing results
        if not descriptions:
            print(f"  WARNING: No descriptions parsed from {model_label} ({prompt_style})")
            print(f"      File exists: {desc_file.exists()}")
            if desc_file.exists():
                print(f"      File size: {desc_file.stat().st_size} bytes")
        
        workflow_data.append((model_label, prompt_style, workflow_name, descriptions))
    
    # Collect all unique (image_name, prompt_style, workflow_name) combinations
    # This ensures we have a row for each image+prompt+workflow combination
    # This allows multiple workflows with the same image and prompt to be tracked separately
    image_prompt_workflow_combinations = set()
    for model_label, prompt_style, workflow_name, descriptions in workflow_data:
        for image_name in descriptions.keys():
            # Use workflow_name if available, otherwise use None
            image_prompt_workflow_combinations.add((image_name, prompt_style, workflow_name))
    
    # Sort combinations based on user preference
    if args.sort == 'date':
        print("Sorting images by date (oldest to newest, extracting EXIF data)...")
        # Create a cache for image dates to avoid repeated EXIF reads
        date_cache = {}
        def get_cached_date(image_name):
            if image_name not in date_cache:
                date_cache[image_name] = get_image_date_for_sorting(image_name, base_dir)
            return date_cache[image_name]
        
        # Sort by: image date, then prompt style, then workflow name  
        sorted_combinations = sorted(image_prompt_workflow_combinations, 
                                    key=lambda x: (get_cached_date(x[0]), x[1], x[2] if x[2] else ''))
        print(f"Sorted {len(set(c[0] for c in sorted_combinations))} unique images by date")
    else:
        # Sort by image name (alphabetically), then by prompt style, then by workflow name
        sorted_combinations = sorted(image_prompt_workflow_combinations, 
                                    key=lambda x: (x[0], x[1], x[2] if x[2] else ''))
        print(f"Sorted {len(set(c[0] for c in sorted_combinations))} unique images alphabetically")
    
    # Get unique model labels for column headers (in order of appearance)
    unique_models = []
    for model_label, _, _, _ in workflow_data:
        if model_label not in unique_models:
            unique_models.append(model_label)
    
    print(f"\nTotal unique images across all workflows: {len(set(c[0] for c in sorted_combinations))}")
    print(f"Total unique prompts: {len(set(c[1] for c in sorted_combinations))}")
    print(f"Total unique workflows: {len(set(c[2] for c in sorted_combinations if c[2]))}")
    print(f"Total image+prompt+workflow combinations: {len(sorted_combinations)}")
    print(f"Total unique models: {len(unique_models)}")
    
    # Create output file - resolve to absolute path
    output_file = Path(args.output).resolve()
    ensure_directory(output_file.parent)
    output_file = get_safe_filename(output_file)
    
    # Determine delimiter and quoting based on format
    if args.format == 'csv':
        delimiter = ','
        quoting = csv.QUOTE_ALL  # Quote all fields for maximum Excel compatibility
        quotechar = '"'
    elif args.format == 'tsv':
        delimiter = '\t'
        quoting = csv.QUOTE_MINIMAL  # Tabs rarely need quoting
        quotechar = '"'
    else:  # atsv
        delimiter = '@'
        quoting = csv.QUOTE_MINIMAL
        quotechar = '"'
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        # Create header row: Image Name, Prompt, Workflow, Model1, Model2, Model3, ...
        headers = ['Image Name', 'Prompt', 'Workflow'] + unique_models
        writer = csv.writer(csvfile, delimiter=delimiter, quoting=quoting, quotechar=quotechar)
        writer.writerow(headers)
        
        # Write data rows for each image+prompt+workflow combination
        for image_name, prompt_style, workflow_name in sorted_combinations:
            row = [image_name, prompt_style, workflow_name if workflow_name else '(legacy)']
            
            # Add description from each model for this image+prompt+workflow combination
            for model_label in unique_models:
                # Find the description for this model+prompt+workflow+image combination
                description = ''
                for wf_model, wf_prompt, wf_workflow_name, wf_descriptions in workflow_data:
                    if (wf_model == model_label and wf_prompt == prompt_style and 
                        wf_workflow_name == workflow_name):
                        description = wf_descriptions.get(image_name, '')
                        break
                row.append(description)
            
            writer.writerow(row)
    
    print(f"\nOutput file created: {output_file}")
    print(f"Format: {args.format.upper()} ({'comma-delimited with quotes' if args.format == 'csv' else 'tab-delimited' if args.format == 'tsv' else '@-delimited'})")
    print(f"Sort order: {'Date (oldest to newest)' if args.sort == 'date' else 'Alphabetical by filename'}")
    print(f"Total rows: {len(sorted_combinations) + 1} (including header)")
    
    if args.format == 'csv':
        print("\n[OK] This CSV file will open directly in Excel with proper column separation!")
    elif args.format == 'tsv':
        print("\n[OK] This TSV file will open directly in Excel with proper column separation!")
    else:
        print("\n[!] To open in Excel: Use Data > From Text/CSV and specify '@' as delimiter")
    
    # Print summary of coverage
    print("\nCoverage summary by model:")
    for model_label in unique_models:
        # Count how many image+prompt+workflow combinations have descriptions for this model
        count = 0
        for wf_model, wf_prompt, wf_workflow_name, wf_descriptions in workflow_data:
            if wf_model == model_label:
                count += len(wf_descriptions)
        print(f"  {model_label}: {count} descriptions")
    
    print("\nPrompts found:")
    prompt_counts = {}
    for _, prompt_style, _, descriptions in workflow_data:
        if prompt_style not in prompt_counts:
            prompt_counts[prompt_style] = 0
        prompt_counts[prompt_style] += len(descriptions)
    for prompt, count in sorted(prompt_counts.items()):
        print(f"  {prompt}: {count} descriptions")
    
    print("\nWorkflows found:")
    workflow_counts = {}
    for _, _, workflow_name, descriptions in workflow_data:
        wf_label = workflow_name if workflow_name else '(legacy - no workflow name)'
        if wf_label not in workflow_counts:
            workflow_counts[wf_label] = 0
        workflow_counts[wf_label] += len(descriptions)
    for wf_name, count in sorted(workflow_counts.items()):
        print(f"  {wf_name}: {count} descriptions")


if __name__ == "__main__":
    main()
