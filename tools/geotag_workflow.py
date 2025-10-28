#!/usr/bin/env python3
"""
Retroactive Metadata & Geocoding for Existing Workflows

This tool updates existing workflow description files by:
1. Extracting metadata (GPS, dates, camera) from original images
2. Adding geocoded location prefixes where missing
3. Preserving existing descriptions while enriching with metadata

Perfect for workflows that were run before metadata extraction was enabled.

Usage:
    python geotag_workflow.py <workflow_dir>
    python geotag_workflow.py C:\\idt\\Descriptions\\wf_VacationPhotos_ollama_llava_narrative_20251027_120000
    
    # With custom geocoding cache
    python geotag_workflow.py <workflow_dir> --geocode-cache my_cache.json
    
    # Dry run (preview changes without modifying files)
    python geotag_workflow.py <workflow_dir> --dry-run
    
    # Update specific file types only
    python geotag_workflow.py <workflow_dir> --only-csv
    python geotag_workflow.py <workflow_dir> --only-txt
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Import IDT modules
try:
    # Try relative imports first (when run from tools/)
    from scripts.metadata_extractor import MetadataExtractor, NominatimGeocoder
except ImportError:
    # Try absolute imports (when run from project root)
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from scripts.metadata_extractor import MetadataExtractor, NominatimGeocoder


class WorkflowGeotagger:
    """Retroactively add metadata and geocoding to workflow results"""
    
    def __init__(self, workflow_dir: Path, geocode: bool = True, 
                 cache_file: Optional[str] = None, dry_run: bool = False):
        self.workflow_dir = Path(workflow_dir)
        self.geocode_enabled = geocode
        self.dry_run = dry_run
        
        # Load file path mappings if available
        self.file_mappings = {}
        mapping_file = self.workflow_dir / 'descriptions' / 'file_path_mapping.json'
        if mapping_file.exists():
            try:
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    self.file_mappings = json.load(f)
                print(f"Loaded {len(self.file_mappings)} file path mappings")
            except Exception as e:
                print(f"WARNING:  Could not load file_path_mapping.json: {e}")
        
        # Initialize metadata extractor
        self.extractor = MetadataExtractor()
        
        # Initialize geocoder if enabled
        self.geocoder = None
        if geocode:
            cache_path = Path(cache_file) if cache_file else Path('geocode_cache.json')
            self.geocoder = NominatimGeocoder(
                user_agent='IDT-Geotag/1.0 (+https://github.com/kellylford/Image-Description-Toolkit)',
                delay_seconds=1.0,
                cache_path=cache_path
            )
            print(f"Geocoding enabled with cache: {cache_path}")
        
        # Statistics
        self.stats = {
            'total_images': 0,
            'metadata_found': 0,
            'geocoded': 0,
            'updated_csv': 0,
            'updated_txt': 0,
            'skipped': 0,
            'errors': 0
        }
    
    def find_image_path(self, relative_path: str) -> Optional[Path]:
        """Find original image file using file_path_mapping.json or fallback search"""
        
        # First try the file mapping (most reliable)
        if self.file_mappings and relative_path in self.file_mappings:
            mapped_path = Path(self.file_mappings[relative_path])
            if mapped_path.exists():
                return mapped_path
        
        # Fallback: try to find in workflow directories
        filename = Path(relative_path).name
        
        # Common locations where images might be
        search_dirs = [
            self.workflow_dir.parent,  # Input directory (one level up from workflow output)
            self.workflow_dir / 'converted_images',
            self.workflow_dir / 'extracted_frames',
        ]
        
        # Search common locations
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
            
            # Try direct match
            candidate = search_dir / filename
            if candidate.exists():
                return candidate
            
            # Try recursive search (for subdirectories)
            for img in search_dir.rglob(filename):
                return img
        
        return None
    
    def extract_metadata_for_image(self, relative_path: str) -> Optional[Dict]:
        """Extract metadata from original image file"""
        
        image_path = self.find_image_path(relative_path)
        if not image_path:
            # For extracted frames, they won't have metadata - skip silently
            if 'extracted_frames' not in relative_path and 'frames' not in relative_path:
                print(f"  WARNING:  Could not locate original image: {relative_path}")
            return None
        
        metadata = self.extractor.extract_metadata(image_path)
        
        if not metadata:
            return None
        
        # Enrich with geocoding if available
        if self.geocoder and 'location' in metadata:
            loc = metadata['location']
            if 'latitude' in loc and 'longitude' in loc:
                metadata = self.geocoder.enrich_metadata(metadata)
        
        return metadata
    
    def format_location_date_prefix(self, metadata: Dict) -> str:
        """Generate location/date prefix from metadata (matches ImageDescriber format)"""
        return self.extractor.format_location_prefix(metadata)
    
    def update_combined_txt_file(self, txt_path: Path) -> int:
        """Update combined image_descriptions.txt file with metadata prefixes"""
        
        if not txt_path.exists():
            return 0
        
        print(f"\n Processing combined descriptions file: {txt_path.name}")
        
        # Read the entire file
        with open(txt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split into sections by separator line
        sections = content.split('--------------------------------------------------------------------------------')
        
        if len(sections) < 2:
            print("  WARNING:  File format not recognized (no separator lines found)")
            return 0
        
        # First section is the header
        header = sections[0]
        updated_sections = [header]
        updated_count = 0
        
        # Process each image section
        for section in sections[1:]:
            section = section.strip()
            if not section:
                continue
            
            self.stats['total_images'] += 1
            
            # Parse section (format: "File: path\nProvider: ...\nModel: ...\nPrompt Style: ...\nDescription: text")
            lines = section.split('\n')
            file_line = None
            desc_start_idx = None
            
            for idx, line in enumerate(lines):
                if line.startswith('File: '):
                    file_line = line
                elif line.startswith('Description: '):
                    desc_start_idx = idx
                    break
            
            if not file_line or desc_start_idx is None:
                updated_sections.append(section)
                self.stats['skipped'] += 1
                continue
            
            # Extract filename and description
            file_path = file_line.replace('File: ', '').strip()
            
            # Get description (everything after "Description: ")
            desc_lines = lines[desc_start_idx:]
            current_desc = desc_lines[0].replace('Description: ', '').strip()
            if len(desc_lines) > 1:
                current_desc += ' ' + ' '.join(line.strip() for line in desc_lines[1:])
            current_desc = current_desc.strip()
            
            # Skip if already has location prefix
            if ', 20' in current_desc[:50] and ':' in current_desc[:50]:
                print(f"  ⏭️  Skipped {Path(file_path).name} (already has prefix)")
                updated_sections.append(section)
                self.stats['skipped'] += 1
                continue
            
            # Extract metadata using the relative path from the file
            metadata = self.extract_metadata_for_image(file_path)
            
            if not metadata:
                print(f"  ℹ️  No metadata for {Path(file_path).name}")
                updated_sections.append(section)
                self.stats['skipped'] += 1
                continue
            
            self.stats['metadata_found'] += 1
            
            # Generate prefix
            prefix = self.format_location_date_prefix(metadata)
            
            if prefix:
                # Add prefix to description
                new_desc = f"{prefix} {current_desc}"
                
                # Rebuild section with updated description
                lines[desc_start_idx] = f"Description: {new_desc}"
                updated_section = '\n'.join(lines)
                updated_sections.append(updated_section)
                
                updated_count += 1
                
                if 'city' in metadata.get('location', {}):
                    self.stats['geocoded'] += 1
                
                print(f"  [OK] Updated {Path(file_path).name}")
                if self.dry_run:
                    print(f"     OLD: {current_desc[:60]}...")
                    print(f"     NEW: {new_desc[:60]}...")
            else:
                updated_sections.append(section)
        
        # Write updated file
        if updated_count > 0 and not self.dry_run:
            # Backup original
            backup_path = txt_path.with_suffix('.txt.bak')
            txt_path.rename(backup_path)
            print(f"  💾 Backup saved: {backup_path.name}")
            
            # Write updated version
            separator = '\n' + '-' * 80 + '\n\n'
            new_content = separator.join(updated_sections)
            
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print(f"  [OK] Updated {updated_count} descriptions")
        
        self.stats['updated_csv'] += updated_count
        return updated_count
    
    def update_txt_files(self, output_dir: Path) -> int:
        """Update individual .txt description files with metadata"""
        
        print(f"\n📝 Processing TXT files in: {output_dir.name}")
        
        txt_files = list(output_dir.glob('*.txt'))
        
        if not txt_files:
            print("  No .txt files found")
            return 0
        
        updated_count = 0
        
        for txt_file in txt_files:
            # Skip special files
            if txt_file.stem in ['workflow_summary', 'failure_report', 'source_images']:
                continue
            
            # Read current content
            with open(txt_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if not content:
                continue
            
            # Skip if already has prefix
            if ', 20' in content[:50] and ':' in content[:50]:
                continue
            
            # Try to find corresponding image
            # txt file might be named like: IMG_1234_description.txt or IMG_1234.txt
            image_name = txt_file.stem.replace('_description', '')
            
            # Look for image with common extensions
            for ext in ['.jpg', '.jpeg', '.png', '.heic', '.JPG', '.JPEG']:
                image_filename = f"{image_name}{ext}"
                metadata = self.extract_metadata_for_image(image_filename)
                
                if metadata:
                    prefix = self.format_location_date_prefix(metadata)
                    
                    if prefix:
                        new_content = f"{prefix} {content}"
                        
                        if not self.dry_run:
                            # Backup
                            backup_path = txt_file.with_suffix('.txt.bak')
                            txt_file.rename(backup_path)
                            
                            # Write updated
                            with open(txt_file, 'w', encoding='utf-8') as f:
                                f.write(new_content)
                        
                        updated_count += 1
                        print(f"  [OK] Updated {txt_file.name}")
                        
                        if 'city' in metadata.get('location', {}):
                            self.stats['geocoded'] += 1
                    
                    break  # Found metadata, stop looking
        
        self.stats['updated_txt'] += updated_count
        return updated_count
    
    def run(self, update_csv: bool = True, update_txt: bool = True):
        """Run the geotagging process"""
        
        if not self.workflow_dir.exists():
            print(f"ERROR: Workflow directory not found: {self.workflow_dir}")
            return False
        
            print("="*70)
            print(f"Retroactive Metadata & Geocoding")
            print("="*70)
        print(f"Workflow: {self.workflow_dir.name}")
        print(f"Mode: {'DRY RUN (preview only)' if self.dry_run else 'LIVE (will modify files)'}")
        print(f"Geocoding: {'Enabled' if self.geocode_enabled else 'Disabled'}")
        print("="*70)
        
        # Look for combined descriptions file (standard IDT format)
        combined_txt = self.workflow_dir / 'descriptions' / 'image_descriptions.txt'
        
        if combined_txt.exists():
            self.update_combined_txt_file(combined_txt)
        else:
            print(f"\nWARNING:  No image_descriptions.txt found in descriptions/ subdirectory")
            print(f"   Expected: {combined_txt}")
        
        # Print summary
        print("\n" + "="*70)
        print("📊 SUMMARY")
        print("="*70)
        print(f"Total images processed: {self.stats['total_images']}")
        print(f"Metadata extracted: {self.stats['metadata_found']}")
        print(f"Geocoded locations: {self.stats['geocoded']}")
        print(f"Descriptions updated: {self.stats['updated_csv']}")
        print(f"Skipped (already tagged/no metadata): {self.stats['skipped']}")
        print(f"Errors: {self.stats['errors']}")
        
        if self.dry_run:
            print("\nWARNING:  DRY RUN: No files were modified")
            print("   Remove --dry-run to apply changes")
        else:
            print("\n[OK] Geotagging complete!")
            print("   Original file backed up with .bak extension")
        
        print("="*70)
        
        return True


def main():
    parser = argparse.ArgumentParser(
        description='Retroactively add metadata and geocoding to existing workflow results',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Geotag a workflow with geocoding
  python geotag_workflow.py C:\\idt\\Descriptions\\wf_VacationPhotos_ollama_llava_narrative_20251027_120000
  
  # Preview changes without modifying (dry run)
  python geotag_workflow.py C:\\idt\\Descriptions\\wf_MyWorkflow_... --dry-run
  
  # Geotag without geocoding (coordinates only)
  python geotag_workflow.py C:\\idt\\Descriptions\\wf_MyWorkflow_... --no-geocode
  
  # Update only CSV file
  python geotag_workflow.py C:\\idt\\Descriptions\\wf_MyWorkflow_... --only-csv
  
  # Custom geocoding cache
  python geotag_workflow.py C:\\idt\\Descriptions\\wf_MyWorkflow_... --geocode-cache my_cache.json
        """
    )
    
    parser.add_argument('workflow_dir', type=str,
                       help='Path to workflow directory to geotag')
    
    parser.add_argument('--no-geocode', action='store_true',
                       help='Skip geocoding (coordinates only, no city/state lookup)')
    
    parser.add_argument('--geocode-cache', type=str, default='geocode_cache.json',
                       help='Geocoding cache file (default: geocode_cache.json)')
    
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview changes without modifying files')
    
    parser.add_argument('--only-csv', action='store_true',
                       help='Update only CSV file (skip individual .txt files)')
    
    parser.add_argument('--only-txt', action='store_true',
                       help='Update only .txt files (skip CSV)')
    
    args = parser.parse_args()
    
    # Determine what to update
    update_csv = not args.only_txt
    update_txt = not args.only_csv
    
    # Create and run geotagger
    geotagger = WorkflowGeotagger(
        workflow_dir=args.workflow_dir,
        geocode=not args.no_geocode,
        cache_file=args.geocode_cache,
        dry_run=args.dry_run
    )
    
    success = geotagger.run(update_csv=update_csv, update_txt=update_txt)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
