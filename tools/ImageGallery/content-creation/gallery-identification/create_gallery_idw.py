#!/usr/bin/env python3
"""
Create IDW (ImageDescriber Workspace) files from gallery identification results.

This module creates IDW files containing images identified by gallery content 
identification, along with all their existing descriptions from workflow results.
This enables seamless viewing of gallery results in ImageDescriber and Viewer.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set
import argparse

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent.parent.parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

try:
    from list_results import find_workflow_directories
except ImportError as e:
    print(f"Error importing list_results: {e}")
    print(f"Scripts directory: {scripts_dir}")
    sys.exit(1)


class GalleryIDWCreator:
    """Creates IDW workspace files from gallery identification results"""
    
    def __init__(self):
        self.workspace_version = "1.0"
    
    def load_gallery_results(self, results_file: Path) -> List[Dict]:
        """Load gallery identification results from JSON file"""
        try:
            with open(results_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle various result formats
            if isinstance(data, dict):
                # New format with candidates
                if 'candidates' in data:
                    return data['candidates']
                # Alternative format with results
                elif 'results' in data:
                    return data['results']
                else:
                    raise ValueError("No 'candidates' or 'results' found in JSON")
            elif isinstance(data, list):
                # Direct list format
                return data
            else:
                raise ValueError("Invalid gallery results format - expected dict or list")
                
        except Exception as e:
            raise Exception(f"Failed to load gallery results: {e}")
    
    def find_image_descriptions(self, image_path: str, workflows_dir: Path) -> List[Dict]:
        """Find all descriptions for an image from workflow results"""
        descriptions = []
        image_file = Path(image_path)
        
        # Find all workflow directories
        workflow_dirs = find_workflow_directories(workflows_dir)
        
        for workflow_path, metadata in workflow_dirs:
            # Look for description files in this workflow
            desc_files = []
            
            # Check for various description file patterns
            possible_names = [
                f"{image_file.stem}.txt",
                f"{image_file.name}.txt",
                image_file.name + ".txt"
            ]
            
            for name in possible_names:
                desc_file = workflow_path / name
                if desc_file.exists():
                    desc_files.append(desc_file)
                    break
            
            # Read description if found
            for desc_file in desc_files:
                try:
                    with open(desc_file, 'r', encoding='utf-8') as f:
                        desc_text = f.read().strip()
                    
                    if desc_text:
                        description = {
                            "id": f"{int(datetime.now().timestamp() * 1000)}_{len(descriptions)}",
                            "text": desc_text,
                            "model": metadata.get("model", "unknown"),
                            "prompt_style": metadata.get("prompt_style", ""),
                            "created": metadata.get("timestamp", datetime.now().isoformat()),
                            "custom_prompt": metadata.get("custom_prompt", ""),
                            "provider": metadata.get("provider", ""),
                            "detection_data": []
                        }
                        descriptions.append(description)
                        
                except Exception as e:
                    print(f"Warning: Could not read description from {desc_file}: {e}")
                    continue
        
        return descriptions
    
    def create_image_item(self, image_path: str, descriptions: List[Dict]) -> Dict:
        """Create an ImageItem dictionary for IDW format"""            
        return {
            "file_path": image_path,  # Use the full path as constructed
            "item_type": "image",
            "descriptions": descriptions,
            "batch_marked": False,
            "parent_video": None,
            "extracted_frames": [],
            "display_name": ""
        }
    
    def create_workspace(self, gallery_results: List[Dict], workflows_dir: Path, 
                        workspace_name: str = None) -> Dict:
        """Create a complete workspace dictionary for IDW format"""
        
        # Collect all unique image paths
        all_image_paths: Set[str] = set()
        directory_paths: Set[str] = set()
        accessible_count = 0
        
        for result in gallery_results:
            filename = result.get("filename", result.get("image_path", ""))
            workflow_path = result.get("workflow_path", "")
            
            if filename and workflow_path:
                # Construct the full path from workflow_path + filename
                full_image_path = str(Path(workflow_path) / filename)
                all_image_paths.add(full_image_path)
                
                # Add the workflow directory as a workspace directory
                directory_paths.add(workflow_path)
                
                # Check if accessible (but don't exclude if not)
                if Path(full_image_path).exists():
                    accessible_count += 1
            elif filename:
                # Fallback to filename only if no workflow_path
                all_image_paths.add(filename)
        
        print(f"Found {len(all_image_paths)} unique images across {len(directory_paths)} directories")
        print(f"Verified {accessible_count}/{len(all_image_paths)} images are accessible")
        
        # Create items with descriptions
        items = {}
        processed_count = 0
        
        # Create a mapping from image paths to their gallery results for description extraction
        results_by_image = {}
        for result in gallery_results:
            filename = result.get("filename", result.get("image_path", ""))
            workflow_path = result.get("workflow_path", "")
            
            if filename and workflow_path:
                # Use the same full path construction as above
                full_image_path = str(Path(workflow_path) / filename)
                if full_image_path not in results_by_image:
                    results_by_image[full_image_path] = []
                results_by_image[full_image_path].append(result)
            elif filename:
                # Fallback for filename only
                if filename not in results_by_image:
                    results_by_image[filename] = []
                results_by_image[filename].append(result)
        
        for image_path in all_image_paths:
            # Start with descriptions from gallery results
            descriptions = []
            
            # Add descriptions from the gallery results themselves
            if image_path in results_by_image:
                for result in results_by_image[image_path]:
                    if result.get("description"):
                        description = {
                            "id": f"{int(datetime.now().timestamp() * 1000)}_{len(descriptions)}",
                            "text": result["description"],
                            "model": result.get("model", "unknown"),
                            "prompt_style": result.get("prompt_style", ""),
                            "created": result.get("timestamp", datetime.now().isoformat()),
                            "custom_prompt": "",
                            "provider": result.get("provider", ""),
                            "detection_data": []
                        }
                        descriptions.append(description)
            
            # Find additional descriptions from workflow directories
            additional_descriptions = self.find_image_descriptions(image_path, workflows_dir)
            descriptions.extend(additional_descriptions)
            
            # Create image item
            image_item = self.create_image_item(image_path, descriptions)
            items[image_path] = image_item
            
            processed_count += 1
            if processed_count % 10 == 0:
                print(f"Processed {processed_count}/{len(all_image_paths)} images...")
        
        print(f"Completed processing {processed_count} images")
        
        # Create workspace
        now = datetime.now().isoformat()
        workspace_name = workspace_name or f"Gallery_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        workspace = {
            "version": self.workspace_version,
            "directory_path": list(directory_paths)[0] if directory_paths else "",  # Legacy compatibility
            "directory_paths": list(directory_paths),
            "items": items,
            "chat_sessions": {},
            "imported_workflow_dir": str(workflows_dir.resolve()),
            "created": now,
            "modified": now
        }
        
        return workspace
    
    def save_idw_file(self, workspace: Dict, output_file: Path):
        """Save workspace as IDW file"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(workspace, f, indent=2)
            print(f"IDW file saved: {output_file}")
            
        except Exception as e:
            raise Exception(f"Failed to save IDW file: {e}")
    
    def create_gallery_idw(self, results_file: Path, workflows_dir: Path, 
                          output_file: Path = None, workspace_name: str = None) -> Path:
        """
        Main function to create IDW file from gallery results
        
        Args:
            results_file: Path to gallery identification results JSON
            workflows_dir: Directory containing workflow results 
            output_file: Output IDW file path (optional)
            workspace_name: Name for the workspace (optional)
            
        Returns:
            Path to created IDW file
        """
        
        # Load gallery results
        print(f"Loading gallery results from: {results_file}")
        gallery_results = self.load_gallery_results(results_file)
        print(f"Loaded {len(gallery_results)} gallery results")
        
        # Create workspace
        print(f"Scanning workflows in: {workflows_dir}")
        workspace = self.create_workspace(gallery_results, workflows_dir, workspace_name)
        
        # Determine output file
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = results_file.parent / f"gallery_workspace_{timestamp}.idw"
        
        # Save IDW file
        self.save_idw_file(workspace, output_file)
        
        # Print summary
        num_images = len(workspace["items"])
        num_dirs = len(workspace["directory_paths"])
        total_descriptions = sum(len(item["descriptions"]) for item in workspace["items"].values())
        
        print(f"\nIDW Workspace Created Successfully!")
        print(f"  File: {output_file}")
        print(f"  Images: {num_images}")
        print(f"  Directories: {num_dirs}")
        print(f"  Total Descriptions: {total_descriptions}")
        print(f"\nTo view: Open {output_file} in ImageDescriber or Viewer")
        
        return output_file


def main():
    """Command line interface"""
    parser = argparse.ArgumentParser(
        description="Create IDW workspace from gallery identification results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python create_gallery_idw.py results.json workflows/ -o gallery.idw
  python create_gallery_idw.py orange_results.json c:/data/workflows/
        """
    )
    
    parser.add_argument("results_file", 
                       help="Gallery identification results JSON file")
    parser.add_argument("workflows_dir",
                       help="Directory containing workflow results")
    parser.add_argument("-o", "--output", 
                       help="Output IDW file path (auto-generated if not specified)")
    parser.add_argument("-n", "--name",
                       help="Workspace name (auto-generated if not specified)")
    
    args = parser.parse_args()
    
    # Validate inputs
    results_file = Path(args.results_file)
    if not results_file.exists():
        print(f"Error: Results file not found: {results_file}")
        sys.exit(1)
    
    workflows_dir = Path(args.workflows_dir)
    if not workflows_dir.exists():
        print(f"Error: Workflows directory not found: {workflows_dir}")
        sys.exit(1)
    
    output_file = Path(args.output) if args.output else None
    
    # Create IDW file
    try:
        creator = GalleryIDWCreator()
        idw_file = creator.create_gallery_idw(
            results_file=results_file,
            workflows_dir=workflows_dir,
            output_file=output_file,
            workspace_name=args.name
        )
        
        print(f"\nSuccess! IDW file created: {idw_file}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()