#!/usr/bin/env python3
"""
Combine descriptions from multiple workflow directories into a single CSV file.

This script reads the image_descriptions.txt files from all workflow directories
and creates a CSV with columns: Image Name, Description1, Description2, etc.
"""

import csv
import re
from pathlib import Path
from typing import Dict, List, Tuple
from collections import OrderedDict


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
    
    Examples:
        wf_claude_claude-3-haiku-20240307_narrative_20251005_172829 -> Claude Haiku
        wf_openai_gpt-4o-mini_narrative_20251005_122700 -> OpenAI GPT-4o-mini
    """
    dir_name = workflow_dir.name
    
    # Extract provider and model from directory name
    # Format: wf_PROVIDER_MODEL_PROMPTSTYLE_DATETIME
    parts = dir_name.split('_')
    
    if len(parts) >= 3:
        provider = parts[1].capitalize()
        model_part = parts[2]
        
        # Clean up common model names
        if 'haiku' in model_part.lower():
            return f"{provider} Haiku"
        elif 'sonnet' in model_part.lower():
            return f"{provider} Sonnet"
        elif 'gpt-4o-mini' in model_part.lower():
            return f"{provider} GPT-4o-mini"
        elif 'llava' in model_part.lower():
            return f"{provider} LLaVA"
        else:
            # Use the model part as-is
            return f"{provider} {model_part}"
    
    return dir_name


def main():
    """Main function to combine workflow descriptions into CSV."""
    
    # Find all workflow directories
    base_dir = Path(__file__).parent
    workflow_dirs = sorted([d for d in base_dir.glob("wf_*") if d.is_dir()])
    
    if not workflow_dirs:
        print("No workflow directories found!")
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
        descriptions = parse_description_file(desc_file)
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
    
    # Create output file with @ delimiter
    output_file = base_dir / "combineddescriptions.txt"
    
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
