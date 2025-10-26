#!/usr/bin/env python3
"""
Gallery Content Identification Tool

Scans described content and identifies images matching gallery criteria
based on keywords, filters, and scoring rules. Configurable via JSON
or command-line parameters.

Usage:
    # Using JSON configuration
    python identify_gallery_content.py --config gallery_config.json
    
    # Using command-line parameters
    python identify_gallery_content.py \
        --scan ./descriptions \
        --required water,sun \
        --keywords sunset,sunrise,reflection \
        --exclude indoor,night \
        --min-matches 2 \
        --max-images 50 \
        --output candidates.json

Features:
    - Configurable data sources (directories, workflow patterns, date ranges)
    - Flexible keyword matching (required, preferred, excluded terms)
    - Advanced filtering (description length, models, prompts)
    - Scoring and ranking system
    - JSON configuration file support
    - Integration with existing build_gallery.py workflow
"""

import argparse
import json
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Set
from collections import defaultdict

# Import utilities from list_results for directory scanning
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "scripts"))
from list_results import find_workflow_directories, count_descriptions, format_timestamp


class GalleryContentIdentifier:
    """Identifies and scores images for gallery inclusion based on criteria."""
    
    def __init__(self, config: Dict):
        """
        Initialize identifier with configuration.
        
        Args:
            config: Configuration dictionary with sources, content_rules, filters, output
        """
        self.config = config
        self.gallery_name = config.get('gallery_name', 'Untitled Gallery')
        self.sources = config.get('sources', {})
        self.content_rules = config.get('content_rules', {})
        self.filters = config.get('filters', {})
        self.output_config = config.get('output', {})
        
        # Set case sensitivity first (needed by _normalize_keywords)
        self.case_sensitive = self.content_rules.get('case_sensitive', False)
        self.min_keyword_matches = self.content_rules.get('min_keyword_matches', 1)
        
        # Process keywords
        self.required_keywords = self._normalize_keywords(
            self.content_rules.get('required_keywords', [])
        )
        self.preferred_keywords = self._normalize_keywords(
            self.content_rules.get('preferred_keywords', [])
        )
        self.excluded_keywords = self._normalize_keywords(
            self.content_rules.get('excluded_keywords', [])
        )
        
        # Filters
        self.min_description_length = self.filters.get('min_description_length', 0)
        self.preferred_prompts = set(self.filters.get('preferred_prompts', []))
        self.preferred_models = set(self.filters.get('preferred_models', []))
        
        # Output settings
        self.max_images = self.output_config.get('max_images', 50)
        self.sort_by = self.output_config.get('sort_by', 'keyword_relevance')
        self.include_metadata = self.output_config.get('include_metadata', True)
        
        # Results storage
        self.candidates = []
        
    def _normalize_keywords(self, keywords: List[str]) -> List[str]:
        """Normalize keywords based on case sensitivity setting."""
        if not self.case_sensitive:
            return [k.lower() for k in keywords]
        return keywords
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for matching based on case sensitivity."""
        if not self.case_sensitive:
            return text.lower()
        return text
    
    def scan_workflows(self) -> List[Tuple[Path, Dict]]:
        """
        Scan directories for workflow results matching criteria.
        
        Returns:
            List of (workflow_path, metadata) tuples
        """
        workflows = []
        directories = self.sources.get('directories', ['./descriptions'])
        workflow_patterns = self.sources.get('workflow_patterns', ['*'])
        date_range = self.sources.get('date_range', {})
        
        for directory in directories:
            dir_path = Path(directory)
            if not dir_path.exists():
                print(f"Warning: Directory does not exist: {directory}")
                continue
            
            # Find all workflows in this directory
            found_workflows = find_workflow_directories(dir_path)
            
            for workflow_path, metadata in found_workflows:
                # Check workflow pattern matching
                if not self._matches_workflow_pattern(workflow_path.name, workflow_patterns):
                    continue
                
                # Check date range if specified
                if date_range and not self._matches_date_range(metadata.get('timestamp', ''), date_range):
                    continue
                
                workflows.append((workflow_path, metadata))
        
        return workflows
    
    def _matches_workflow_pattern(self, workflow_name: str, patterns: List[str]) -> bool:
        """Check if workflow name matches any of the patterns."""
        if not patterns or patterns == ['*']:
            return True
        
        workflow_lower = workflow_name.lower()
        for pattern in patterns:
            pattern_lower = pattern.lower()
            # Simple wildcard matching - strip * and check if substring is present
            if pattern_lower == '*':
                return True
            # Remove wildcards and check if the term is in the workflow name
            search_term = pattern_lower.replace('*', '')
            if search_term in workflow_lower:
                return True
        return False
    
    def _matches_date_range(self, timestamp_str: str, date_range: Dict) -> bool:
        """Check if timestamp falls within date range."""
        if not timestamp_str or timestamp_str == 'unknown':
            return False
        
        try:
            # Parse timestamp (YYYYMMDD_HHMMSS format)
            if '_' in timestamp_str:
                date_part = timestamp_str.split('_')[0]
            else:
                date_part = timestamp_str[:8]
            
            ts_date = datetime.strptime(date_part, "%Y%m%d").date()
            
            start_str = date_range.get('start')
            end_str = date_range.get('end')
            
            if start_str:
                start_date = datetime.strptime(start_str, "%Y-%m-%d").date()
                if ts_date < start_date:
                    return False
            
            if end_str:
                end_date = datetime.strptime(end_str, "%Y-%m-%d").date()
                if ts_date > end_date:
                    return False
            
            return True
        except Exception:
            return False
    
    def extract_descriptions_from_workflow(self, workflow_path: Path) -> List[Dict]:
        """
        Extract image descriptions from a workflow directory.
        
        Args:
            workflow_path: Path to workflow directory
            
        Returns:
            List of description dictionaries
        """
        descriptions = []
        desc_file = workflow_path / 'descriptions' / 'image_descriptions.txt'
        
        if not desc_file.exists():
            return descriptions
        
        try:
            with open(desc_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split by separator lines
            blocks = re.split(r'\n-{40,}\n', content)
            
            for block in blocks:
                if not block.strip():
                    continue
                
                desc_data = self._parse_description_block(block)
                if desc_data:
                    descriptions.append(desc_data)
        
        except Exception as e:
            print(f"Error reading descriptions from {workflow_path.name}: {e}")
        
        return descriptions
    
    def _parse_description_block(self, block: str) -> Optional[Dict]:
        """Parse a description block into structured data."""
        data = {}
        
        # Extract fields using regex
        file_match = re.search(r'^File:\s*(.+)$', block, re.MULTILINE)
        
        # Match description until we hit another field or end of block
        # The lookahead checks for: newline + field name, or end of string (\Z)
        # This allows multi-line descriptions that stop at the next field
        desc_match = re.search(r'^Description:\s*(.+?)(?:\n(?=Provider:|Model:|Prompt:|Cost:|Tokens:|Time:)|\Z)', 
                              block, re.MULTILINE | re.DOTALL)
        
        provider_match = re.search(r'^Provider:\s*(.+)$', block, re.MULTILINE)
        model_match = re.search(r'^Model:\s*(.+)$', block, re.MULTILINE)
        prompt_match = re.search(r'^Prompt Style:\s*(.+)$', block, re.MULTILINE)
        
        if file_match and desc_match:
            data['filename'] = file_match.group(1).strip()
            data['description'] = desc_match.group(1).strip()
            data['provider'] = provider_match.group(1).strip() if provider_match else 'unknown'
            data['model'] = model_match.group(1).strip() if model_match else 'unknown'
            data['prompt_style'] = prompt_match.group(1).strip() if prompt_match else 'unknown'
            return data
        
        return None
    
    def score_description(self, description_text: str, metadata: Dict) -> Tuple[float, Dict]:
        """
        Score a description based on keyword matches and filters.
        
        Args:
            description_text: The description text to score
            metadata: Additional metadata (provider, model, prompt_style)
            
        Returns:
            Tuple of (score, match_details)
        """
        score = 0.0
        details = {
            'required_matches': [],
            'preferred_matches': [],
            'excluded_matches': [],
            'filter_bonuses': {},
            'passes_filters': True
        }
        
        # Normalize text
        normalized_desc = self._normalize_text(description_text)
        
        # Check for excluded keywords first (immediate disqualification)
        for keyword in self.excluded_keywords:
            if keyword in normalized_desc:
                details['excluded_matches'].append(keyword)
                details['passes_filters'] = False
                return -1000.0, details  # Negative score to exclude
        
        # Check required keywords (must have ALL)
        for keyword in self.required_keywords:
            if keyword in normalized_desc:
                details['required_matches'].append(keyword)
                score += 10.0  # High weight for required keywords
            else:
                # Missing a required keyword
                details['passes_filters'] = False
                return 0.0, details
        
        # Check preferred keywords (nice to have)
        for keyword in self.preferred_keywords:
            if keyword in normalized_desc:
                details['preferred_matches'].append(keyword)
                score += 5.0  # Medium weight for preferred keywords
        
        # Check minimum keyword matches
        total_matches = len(details['required_matches']) + len(details['preferred_matches'])
        if total_matches < self.min_keyword_matches:
            details['passes_filters'] = False
            return 0.0, details
        
        # Apply filters and bonuses
        
        # Description length filter
        if len(description_text) < self.min_description_length:
            details['passes_filters'] = False
            return 0.0, details
        
        # Preferred model bonus
        if self.preferred_models and metadata.get('model') in self.preferred_models:
            score += 3.0
            details['filter_bonuses']['preferred_model'] = True
        
        # Preferred prompt bonus
        if self.preferred_prompts and metadata.get('prompt_style') in self.preferred_prompts:
            score += 2.0
            details['filter_bonuses']['preferred_prompt'] = True
        
        return score, details
    
    def identify_candidates(self) -> List[Dict]:
        """
        Main method to identify candidate images for the gallery.
        
        Returns:
            List of candidate image dictionaries with scores
        """
        print(f"\n🔍 Identifying candidates for: {self.gallery_name}")
        print(f"=" * 70)
        
        # Scan workflows
        print("\n📁 Scanning workflow directories...")
        workflows = self.scan_workflows()
        print(f"   Found {len(workflows)} workflow(s) matching criteria")
        
        if not workflows:
            print("\n⚠️  No workflows found matching the specified criteria")
            return []
        
        # Process each workflow
        all_candidates = []
        processed_images = set()  # Track unique images across workflows
        
        print("\n📝 Processing descriptions...")
        for workflow_path, workflow_metadata in workflows:
            descriptions = self.extract_descriptions_from_workflow(workflow_path)
            
            for desc_data in descriptions:
                filename = desc_data['filename']
                description = desc_data['description']
                
                # Score this description
                metadata = {
                    'provider': desc_data.get('provider', 'unknown'),
                    'model': desc_data.get('model', 'unknown'),
                    'prompt_style': desc_data.get('prompt_style', 'unknown')
                }
                
                score, match_details = self.score_description(description, metadata)
                
                # Only include if passes filters and has positive score
                if match_details['passes_filters'] and score > 0:
                    candidate = {
                        'filename': filename,
                        'score': score,
                        'workflow_path': str(workflow_path),
                        'workflow_name': workflow_metadata.get('workflow_name', 'unknown'),
                        'description': description,
                        'match_details': match_details
                    }
                    
                    if self.include_metadata:
                        candidate.update({
                            'provider': metadata['provider'],
                            'model': metadata['model'],
                            'prompt_style': metadata['prompt_style'],
                            'timestamp': workflow_metadata.get('timestamp', 'unknown')
                        })
                    
                    all_candidates.append(candidate)
                    processed_images.add(filename)
        
        print(f"   ✅ Found {len(all_candidates)} matching descriptions from {len(processed_images)} unique images")
        
        # Sort by score (or other criteria)
        if self.sort_by == 'keyword_relevance':
            all_candidates.sort(key=lambda x: x['score'], reverse=True)
        elif self.sort_by == 'filename':
            all_candidates.sort(key=lambda x: x['filename'])
        
        # Limit to max_images
        if self.max_images > 0 and len(all_candidates) > self.max_images:
            all_candidates = all_candidates[:self.max_images]
            print(f"   📊 Limited to top {self.max_images} candidates")
        
        self.candidates = all_candidates
        return all_candidates
    
    def print_summary(self):
        """Print summary of identified candidates."""
        if not self.candidates:
            print("\n⚠️  No candidates identified")
            return
        
        print(f"\n📊 Summary")
        print(f"=" * 70)
        print(f"Gallery Name: {self.gallery_name}")
        print(f"Total Candidates: {len(self.candidates)}")
        
        # Score statistics
        scores = [c['score'] for c in self.candidates]
        print(f"\nScore Range: {min(scores):.1f} - {max(scores):.1f}")
        print(f"Average Score: {sum(scores) / len(scores):.1f}")
        
        # Keyword match statistics
        required_matches = sum(len(c['match_details']['required_matches']) for c in self.candidates)
        preferred_matches = sum(len(c['match_details']['preferred_matches']) for c in self.candidates)
        print(f"\nKeyword Matches:")
        print(f"  Required: {required_matches} total")
        print(f"  Preferred: {preferred_matches} total")
        
        # Top candidates preview
        print(f"\n🏆 Top 5 Candidates:")
        for i, candidate in enumerate(self.candidates[:5], 1):
            print(f"\n  {i}. {candidate['filename']} (Score: {candidate['score']:.1f})")
            required = candidate['match_details']['required_matches']
            preferred = candidate['match_details']['preferred_matches']
            if required:
                print(f"     Required: {', '.join(required)}")
            if preferred:
                print(f"     Preferred: {', '.join(preferred)}")
    
    def save_results(self, output_path: Path):
        """Save identified candidates to JSON file."""
        output_data = {
            'gallery_name': self.gallery_name,
            'generated_at': datetime.now().isoformat(),
            'configuration': {
                'required_keywords': self.required_keywords,
                'preferred_keywords': self.preferred_keywords,
                'excluded_keywords': self.excluded_keywords,
                'min_keyword_matches': self.min_keyword_matches,
                'max_images': self.max_images
            },
            'total_candidates': len(self.candidates),
            'candidates': self.candidates
        }
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            print(f"\n💾 Results saved to: {output_path}")
            print(f"   {len(self.candidates)} candidates written")
            return True
        except Exception as e:
            print(f"\n❌ Error saving results: {e}")
            return False


def load_config_file(config_path: Path) -> Dict:
    """Load configuration from JSON file."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"Error loading config file: {e}")
        sys.exit(1)


def build_config_from_args(args) -> Dict:
    """Build configuration dictionary from command-line arguments."""
    config = {
        'gallery_name': args.name or 'Untitled Gallery',
        'sources': {
            'directories': args.scan if args.scan else ['./descriptions'],
            'workflow_patterns': args.workflow_patterns.split(',') if args.workflow_patterns else ['*'],
        },
        'content_rules': {
            'required_keywords': args.required.split(',') if args.required else [],
            'preferred_keywords': args.keywords.split(',') if args.keywords else [],
            'excluded_keywords': args.exclude.split(',') if args.exclude else [],
            'min_keyword_matches': args.min_matches,
            'case_sensitive': args.case_sensitive
        },
        'filters': {
            'min_description_length': args.min_length,
            'preferred_prompts': args.prompts.split(',') if args.prompts else [],
            'preferred_models': args.models.split(',') if args.models else []
        },
        'output': {
            'max_images': args.max_images,
            'sort_by': args.sort_by,
            'include_metadata': not args.no_metadata
        }
    }
    
    # Add date range if specified
    if args.date_start or args.date_end:
        config['sources']['date_range'] = {}
        if args.date_start:
            config['sources']['date_range']['start'] = args.date_start
        if args.date_end:
            config['sources']['date_range']['end'] = args.date_end
    
    return config


def main():
    """Main entry point for the gallery content identifier."""
    parser = argparse.ArgumentParser(
        description="Identify images for gallery based on description keywords and filters",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using JSON configuration file
  python identify_gallery_content.py --config sunset_gallery.json
  
  # Using command-line parameters
  python identify_gallery_content.py \\
    --name "Sunshine On The Water Makes Me Happy" \\
    --scan ./descriptions \\
    --required water,sun \\
    --keywords sunset,sunrise,reflection,clouds,moon \\
    --exclude indoor,night,dark \\
    --min-matches 2 \\
    --max-images 50 \\
    --output ./gallery_candidates.json
  
  # Multiple scan directories
  python identify_gallery_content.py \\
    --scan ./descriptions //qnap/home/idt/descriptions \\
    --required water \\
    --keywords ocean,lake,river,beach \\
    --output water_scenes.json
        """
    )
    
    # Configuration source
    config_group = parser.add_mutually_exclusive_group()
    config_group.add_argument(
        '--config', '-c',
        type=Path,
        help='JSON configuration file path'
    )
    
    # Gallery settings
    parser.add_argument(
        '--name', '-n',
        help='Gallery name (default: "Untitled Gallery")'
    )
    
    # Source directories
    parser.add_argument(
        '--scan', '-s',
        nargs='+',
        help='Directories to scan for workflows (default: ./descriptions)'
    )
    
    parser.add_argument(
        '--workflow-patterns',
        help='Comma-separated workflow name patterns to include (default: *)'
    )
    
    parser.add_argument(
        '--date-start',
        help='Start date for filtering (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--date-end',
        help='End date for filtering (YYYY-MM-DD)'
    )
    
    # Keyword rules
    parser.add_argument(
        '--required', '-r',
        help='Comma-separated required keywords (must have ALL)'
    )
    
    parser.add_argument(
        '--keywords', '-k',
        help='Comma-separated preferred keywords (nice to have)'
    )
    
    parser.add_argument(
        '--exclude', '-e',
        help='Comma-separated excluded keywords (filter out)'
    )
    
    parser.add_argument(
        '--min-matches',
        type=int,
        default=1,
        help='Minimum total keyword matches required (default: 1)'
    )
    
    parser.add_argument(
        '--case-sensitive',
        action='store_true',
        help='Use case-sensitive keyword matching'
    )
    
    # Filters
    parser.add_argument(
        '--min-length',
        type=int,
        default=0,
        help='Minimum description length (default: 0)'
    )
    
    parser.add_argument(
        '--prompts',
        help='Comma-separated preferred prompt styles'
    )
    
    parser.add_argument(
        '--models',
        help='Comma-separated preferred models'
    )
    
    # Output settings
    parser.add_argument(
        '--max-images',
        type=int,
        default=50,
        help='Maximum number of images to return (default: 50, 0 = unlimited)'
    )
    
    parser.add_argument(
        '--sort-by',
        choices=['keyword_relevance', 'filename'],
        default='keyword_relevance',
        help='Sort method for results (default: keyword_relevance)'
    )
    
    parser.add_argument(
        '--no-metadata',
        action='store_true',
        help='Exclude metadata from output'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=Path,
        default=Path('gallery_candidates.json'),
        help='Output JSON file path (default: gallery_candidates.json)'
    )
    
    args = parser.parse_args()
    
    # Load or build configuration
    if args.config:
        if not args.config.exists():
            print(f"Error: Configuration file not found: {args.config}")
            return 1
        config = load_config_file(args.config)
    else:
        # Build config from command-line args
        if not args.required and not args.keywords:
            print("Error: Must specify either --config or at least one of --required/--keywords")
            parser.print_help()
            return 1
        config = build_config_from_args(args)
    
    # Create identifier and run
    identifier = GalleryContentIdentifier(config)
    candidates = identifier.identify_candidates()
    
    # Print summary
    identifier.print_summary()
    
    # Save results
    if candidates:
        identifier.save_results(args.output)
        print(f"\n✅ Gallery content identification complete!")
        print(f"\n💡 Next steps:")
        print(f"   1. Review candidates in {args.output}")
        print(f"   2. Copy selected images to gallery/images/")
        print(f"   3. Run build_gallery.py to finalize")
    else:
        print(f"\n⚠️  No candidates found. Try:")
        print(f"   - Relaxing keyword requirements")
        print(f"   - Checking workflow directories exist")
        print(f"   - Verifying description files are present")
    
    return 0 if candidates else 1


if __name__ == '__main__':
    sys.exit(main())
