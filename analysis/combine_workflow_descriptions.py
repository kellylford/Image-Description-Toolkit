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
import re
from pathlib import Path
from typing import Dict, List, Tuple
from collections import OrderedDict
from analysis_utils import get_safe_filename, ensure_directory


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
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            # Check for file marker
            if line.startswith("File: "):
                # Save previous description if exists
                if current_file and current_description:
                    desc_text = ' '.join(current_description).strip()
                    descriptions[current_file] = desc_text
                    current_description = []
                
                # Extract file path and normalize to just the image name
                file_path_str = line[6:].strip()  # Remove "File: " prefix
                # Extract just the filename from paths like "converted_images\IMG_3136.jpg"
                # or "extracted_frames\IMG_3136\IMG_3136_0.00s.jpg" or "09\IMG_3137.PNG"
                current_file = Path(file_path_str).name
                
            # Check for description marker
            elif line.startswith("Description: "):
                desc_text = line[13:].strip()  # Remove "Description: " prefix
                current_description.append(desc_text)
                
            # Check for separator (end of description block)
            elif line.startswith("---"):
                # Save the description we were building
                if current_file and current_description:
                    # Join and clean up extra spaces
                    desc_text = ' '.join(current_description).strip()
                    # Clean up multiple consecutive spaces
                    desc_text = ' '.join(desc_text.split())
                    descriptions[current_file] = desc_text
                    current_description = []
                    current_file = None
                    
            # Continue multi-line description (including empty lines between paragraphs)
            elif current_file and current_description:
                # This is a continuation of the description
                # Keep empty lines to preserve paragraph breaks
                if line.strip():
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
    
    # Known prompt styles
    prompt_styles = ['narrative', 'detailed', 'concise', 'technical', 'creative', 'colorful', 'artistic']
    
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
  # Create standard CSV (opens directly in Excel)
  python combine_workflow_descriptions.py
  
  # Create tab-separated file (also opens directly in Excel)
  python combine_workflow_descriptions.py --format tsv --output results.tsv
  
  # Use legacy @-separated format (requires import wizard in Excel)
  python combine_workflow_descriptions.py --format atsv --output results.txt
  
  # Specify custom workflow directory
  python combine_workflow_descriptions.py --input-dir /path/to/workflows
  
  # Use both custom input and format
  python combine_workflow_descriptions.py --input-dir /data/workflows --format tsv
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
        default='combineddescriptions.csv',
        help='Output filename (default: combineddescriptions.csv). Saved in analysis/ directory.'
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
    
    args = parser.parse_args()
    
    # Determine input directory
    if args.input_dir:
        base_dir = args.input_dir
    else:
        # Default to ../Descriptions relative to this script
        base_dir = Path(__file__).parent.parent / "Descriptions"
    
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
    workflow_data = []  # List of (model_label, prompt_style, descriptions_dict)
    
    for workflow_dir in workflow_dirs:
        desc_file = workflow_dir / "descriptions" / "image_descriptions.txt"
        model_label, prompt_style = get_workflow_label(workflow_dir)
        
        # Debug: Check if file exists
        if not desc_file.exists():
            print(f"  ⚠️  WARNING: Description file not found for {model_label} ({prompt_style})")
            print(f"      Expected: {desc_file}")
        
        descriptions = parse_description_file(desc_file)
        
        # Debug: Report parsing results
        if not descriptions:
            print(f"  WARNING: No descriptions parsed from {model_label} ({prompt_style})")
            print(f"      File exists: {desc_file.exists()}")
            if desc_file.exists():
                print(f"      File size: {desc_file.stat().st_size} bytes")
        
        workflow_data.append((model_label, prompt_style, descriptions))
    
    # Collect all unique (image_name, prompt_style) combinations
    # This ensures we have a row for each image+prompt combination
    image_prompt_combinations = set()
    for model_label, prompt_style, descriptions in workflow_data:
        for image_name in descriptions.keys():
            image_prompt_combinations.add((image_name, prompt_style))
    
    # Sort combinations: first by image name, then by prompt style
    sorted_combinations = sorted(image_prompt_combinations, key=lambda x: (x[0], x[1]))
    
    # Get unique model labels for column headers (in order of appearance)
    unique_models = []
    for model_label, _, _ in workflow_data:
        if model_label not in unique_models:
            unique_models.append(model_label)
    
    print(f"\nTotal unique images across all workflows: {len(set(c[0] for c in sorted_combinations))}")
    print(f"Total unique prompts: {len(set(c[1] for c in sorted_combinations))}")
    print(f"Total image+prompt combinations: {len(sorted_combinations)}")
    print(f"Total unique models: {len(unique_models)}")
    
    # Create output file in analysis directory with safe filename
    output_dir = Path(__file__).parent
    ensure_directory(output_dir)
    
    output_file = output_dir / args.output
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
        # Create header row: Image Name, Prompt, Model1, Model2, Model3, ...
        headers = ['Image Name', 'Prompt'] + unique_models
        writer = csv.writer(csvfile, delimiter=delimiter, quoting=quoting, quotechar=quotechar)
        writer.writerow(headers)
        
        # Write data rows for each image+prompt combination
        for image_name, prompt_style in sorted_combinations:
            row = [image_name, prompt_style]
            
            # Add description from each model for this image+prompt combination
            for model_label in unique_models:
                # Find the description for this model+prompt+image combination
                description = ''
                for wf_model, wf_prompt, wf_descriptions in workflow_data:
                    if wf_model == model_label and wf_prompt == prompt_style:
                        description = wf_descriptions.get(image_name, '')
                        break
                row.append(description)
            
            writer.writerow(row)
    
    print(f"\nOutput file created: {output_file}")
    print(f"Format: {args.format.upper()} ({'comma-delimited with quotes' if args.format == 'csv' else 'tab-delimited' if args.format == 'tsv' else '@-delimited'})")
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
        # Count how many image+prompt combinations have descriptions for this model
        count = 0
        for wf_model, wf_prompt, wf_descriptions in workflow_data:
            if wf_model == model_label:
                count += len(wf_descriptions)
        print(f"  {model_label}: {count} descriptions")
    
    print("\nPrompts found:")
    prompt_counts = {}
    for _, prompt_style, descriptions in workflow_data:
        if prompt_style not in prompt_counts:
            prompt_counts[prompt_style] = 0
        prompt_counts[prompt_style] += len(descriptions)
    for prompt, count in sorted(prompt_counts.items()):
        print(f"  {prompt}: {count} descriptions")


if __name__ == "__main__":
    main()
