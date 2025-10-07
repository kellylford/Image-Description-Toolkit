#!/usr/bin/env python3
"""
Combine descriptions from multiple workflow directories into a single CSV file.

This script reads the image_descriptions.txt files from all workflow directories
and creates a CSV with columns: Image Name, Description1, Description2, etc.
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


def get_workflow_label(workflow_dir: Path) -> str:
    """
    Extract a readable label from the workflow directory name.
    Creates unique, distinguishable labels for all models.
    
    Examples:
        wf_claude_claude-3-haiku-20240307_narrative_... -> Claude Haiku 3
        wf_claude_claude-3-5-haiku-20241022_narrative_... -> Claude Haiku 3.5
        wf_ollama_llava_7b_narrative_... -> Ollama LLaVA 7B
        wf_ollama_llava_13b_narrative_... -> Ollama LLaVA 13B
        wf_openai_gpt-4o-mini_narrative_... -> OpenAI GPT-4o-mini
    """
    dir_name = workflow_dir.name
    
    # Extract provider and model from directory name
    # Format: wf_PROVIDER_MODEL_VARIANT_PROMPTSTYLE_DATETIME
    parts = dir_name.split('_')
    
    if len(parts) >= 3:
        provider = parts[1].capitalize()
        model_part = parts[2]
        
        # For models with size/variant in parts[3], include it
        variant = parts[3] if len(parts) > 3 and parts[3] not in ['narrative', 'detailed', 'concise'] else None
        
        # Create readable labels for Claude models
        if provider.lower() == 'claude':
            # claude-3-haiku-20240307 -> Haiku 3
            # claude-3-5-haiku-20241022 -> Haiku 3.5
            # claude-opus-4-1-20250805 -> Opus 4.1
            # claude-sonnet-4-5-20250929 -> Sonnet 4.5
            if 'haiku' in model_part:
                if '3-5' in model_part:
                    return "Claude Haiku 3.5"
                else:
                    return "Claude Haiku 3"
            elif 'sonnet' in model_part:
                if '4-5' in model_part:
                    return "Claude Sonnet 4.5"
                elif '3-7' in model_part:
                    return "Claude Sonnet 3.7"
                elif 'sonnet-4' in model_part:
                    return "Claude Sonnet 4"
                else:
                    return "Claude Sonnet"
            elif 'opus' in model_part:
                if '4-1' in model_part:
                    return "Claude Opus 4.1"
                elif 'opus-4-2' in model_part:
                    return "Claude Opus 4"
                else:
                    return "Claude Opus"
        
        # Create readable labels for Ollama models
        elif provider.lower() == 'ollama':
            # llava with variant (7b, 13b, 34b, latest)
            if 'llava' in model_part and variant:
                base = "LLaVA"
                if 'phi3' in model_part:
                    base = "LLaVA-Phi3"
                elif 'llama3' in model_part:
                    base = "LLaVA-Llama3"
                
                # Format variant nicely
                if variant == 'latest':
                    return f"Ollama {base}"
                elif variant.endswith('b'):  # 7b, 13b, 34b
                    return f"Ollama {base} {variant.upper()}"
                else:
                    return f"Ollama {base} {variant}"
            
            # llama3.2-vision with variant (11b, 90b, latest)
            elif 'llama3.2-vision' in model_part or 'llama3-2-vision' in model_part:
                if variant == 'latest':
                    return "Ollama Llama3.2-Vision"
                elif variant.endswith('b'):
                    return f"Ollama Llama3.2-Vision {variant.upper()}"
                else:
                    return f"Ollama Llama3.2-Vision {variant}"
            
            # Other Ollama models (moondream, bakllava, etc.)
            elif model_part == 'moondream':
                return "Ollama Moondream"
            elif model_part == 'bakllava':
                return "Ollama BakLLaVA"
            elif 'minicpm' in model_part:
                if variant and variant.endswith('b'):
                    return f"Ollama MiniCPM-V {variant.upper()}"
                else:
                    return "Ollama MiniCPM-V"
            elif model_part == 'cogvlm2':
                return "Ollama CogVLM2"
            elif model_part == 'internvl':
                return "Ollama InternVL"
            else:
                # Generic fallback for Ollama
                if variant and variant != 'latest':
                    return f"Ollama {model_part.title()} {variant}"
                else:
                    return f"Ollama {model_part.title()}"
        
        # OpenAI models
        elif provider.lower() == 'openai':
            # gpt-4o, gpt-4o-mini, gpt-5
            if 'gpt-4o-mini' in model_part:
                return "OpenAI GPT-4o-mini"
            elif 'gpt-4o' in model_part:
                return "OpenAI GPT-4o"
            elif 'gpt-5' in model_part:
                return "OpenAI GPT-5"
            else:
                return f"OpenAI {model_part.upper()}"
        
        # Generic fallback for any other providers
        else:
            if variant and variant != 'latest':
                return f"{provider} {model_part} {variant}"
            else:
                return f"{provider} {model_part}"
    
    return dir_name


def main():
    """Main function to combine workflow descriptions into CSV."""
    parser = argparse.ArgumentParser(
        description='Combine descriptions from multiple workflow directories into a single CSV file.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Use default Descriptions directory
  python combine_workflow_descriptions.py
  
  # Specify custom workflow directory
  python combine_workflow_descriptions.py --input-dir /path/to/workflows
  
  # Specify custom output filename
  python combine_workflow_descriptions.py --output my_combined_descriptions.csv
  
  # Use both custom input and output
  python combine_workflow_descriptions.py --input-dir /data/workflows --output results.csv
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
        default='combineddescriptions.txt',
        help='Output filename (default: combineddescriptions.txt). Saved in analysis/ directory.'
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
    all_descriptions = []
    workflow_labels = []
    
    for workflow_dir in workflow_dirs:
        desc_file = workflow_dir / "descriptions" / "image_descriptions.txt"
        label = get_workflow_label(workflow_dir)
        workflow_labels.append(label)
        
        # Debug: Check if file exists
        if not desc_file.exists():
            print(f"  ⚠️  WARNING: Description file not found for {label}")
            print(f"      Expected: {desc_file}")
        
        descriptions = parse_description_file(desc_file)
        
        # Debug: Report parsing results
        if not descriptions:
            print(f"  WARNING: No descriptions parsed from {label}")
            print(f"      File exists: {desc_file.exists()}")
            if desc_file.exists():
                print(f"      File size: {desc_file.stat().st_size} bytes")
        
        all_descriptions.append(descriptions)
    
    # Use the first workflow's order as the primary ordering (preserves processing order)
    # Then add any additional images from other workflows
    if all_descriptions:
        # Start with the first workflow's order (should be the most complete)
        primary_order = list(all_descriptions[0].keys())
        
        # Add any images that appear in other workflows but not in the first
        all_image_names = set()
        for descriptions in all_descriptions:
            all_image_names.update(descriptions.keys())
        
        # Add missing images in alphabetical order at the end
        missing_images = sorted(all_image_names - set(primary_order))
        image_order = primary_order + missing_images
    else:
        image_order = []
    
    print(f"\nTotal unique images across all workflows: {len(image_order)}")
    print(f"Sort order: Processing order from first workflow ({workflow_labels[0] if workflow_labels else 'N/A'})")
    
    # Create output file in analysis directory with safe filename
    output_dir = Path(__file__).parent
    ensure_directory(output_dir)
    
    output_file = output_dir / args.output
    output_file = get_safe_filename(output_file)
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        # Create header row
        headers = ['Image Name'] + workflow_labels
        writer = csv.writer(csvfile, delimiter='@')
        writer.writerow(headers)
        
        # Write data rows in processing order
        for image_name in image_order:
            row = [image_name]
            
            # Add description from each workflow (or empty string if not found)
            for descriptions in all_descriptions:
                description = descriptions.get(image_name, '')
                row.append(description)
            
            writer.writerow(row)
    
    print(f"\nOutput file created: {output_file}")
    print(f"Total rows: {len(image_order) + 1} (including header)")
    
    # Print summary of coverage
    print("\nCoverage summary:")
    for i, label in enumerate(workflow_labels):
        count = len(all_descriptions[i])
        percentage = (count / len(image_order) * 100) if image_order else 0
        print(f"  {label}: {count} images ({percentage:.1f}%)")


if __name__ == "__main__":
    main()
