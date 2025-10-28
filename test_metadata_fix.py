#!/usr/bin/env python3
"""Quick test to verify the metadata format string fix"""

import sys
sys.path.append('scripts')

from metadata_extractor import MetadataExtractor

# Create a test scenario with problematic location data
test_metadata = {
    'location': {
        'city': 'Madison {Test}',  # City with curly braces
        'state': 'WI {State}',     # State with curly braces  
        'country': 'USA'
    },
    'camera': {
        'make': 'Apple {Brand}',   # Make with curly braces
        'model': 'iPhone {14}'     # Model with curly braces
    },
    'date_short': 'Jan 1, 2025'
}

print("Testing metadata format string fix...")
print("Test data contains curly braces that would cause format string errors")
print()

extractor = MetadataExtractor()

try:
    # Test the format_location_prefix method
    location_prefix = extractor.format_location_prefix(test_metadata)
    print(f"✅ format_location_prefix: SUCCESS - '{location_prefix}'")
except Exception as e:
    print(f"❌ format_location_prefix: FAILED - {e}")

try:
    # Test the build_meta_suffix method
    from pathlib import Path
    meta_suffix = extractor.build_meta_suffix(Path("test.jpg"), test_metadata)
    print(f"✅ build_meta_suffix: SUCCESS - '{meta_suffix}'")
except Exception as e:
    print(f"❌ build_meta_suffix: FAILED - {e}")

print()
print("=== TESTING COMPLETE ===")
print("If both tests show SUCCESS, the format string fix is working!")