#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for IDW workflow functionality

Tests the basic IDW workflow integration to ensure it works properly
before integration with ImageDescriber.

Author: Image Description Toolkit
Date: September 16, 2025
"""

import tempfile
import shutil
from pathlib import Path
from typing import List
import sys

# Add scripts directory to path
sys.path.append(str(Path(__file__).parent.parent / "scripts"))

try:
    from workflow_idw_integration import create_workflow_with_idw, export_html_from_idw
except ImportError as e:
    print(f"Failed to import workflow_idw_integration: {e}")
    sys.exit(1)


def create_test_images(test_dir: Path) -> List[Path]:
    """Create some dummy image files for testing"""
    image_files = []
    for i in range(3):
        img_file = test_dir / f"test_image_{i:02d}.jpg"
        # Create a dummy file (not a real image, just for testing)
        img_file.write_text(f"Dummy image content {i}")
        image_files.append(img_file)
    return image_files


def test_idw_workflow():
    """Test basic IDW workflow functionality"""
    print("🧪 Testing IDW Workflow Integration...")
    
    # Create temporary test directory
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir)
        input_dir = test_dir / "input"
        input_dir.mkdir()
        
        # Create test files
        image_files = create_test_images(input_dir)
        print(f"📁 Created {len(image_files)} test files in {input_dir}")
        
        # IDW output path
        idw_path = test_dir / "test_workflow.idw"
        
        # Processing configuration
        processing_config = {
            "model": "test_model",
            "prompt_style": "test_style",
            "provider": "test",
            "custom_prompt": None,
            "conversion_settings": {
                "heic_to_jpeg": False,
                "video_frame_extraction": False
            }
        }
        
        try:
            # Initialize IDW workflow
            print("🔧 Initializing IDW workflow...")
            integration = create_workflow_with_idw(
                input_dir, idw_path, processing_config, resume=False
            )
            
            # Process items
            total_processed = 0
            while not integration.is_processing_complete():
                items = integration.get_next_items_to_process(batch_size=1)
                if not items:
                    break
                
                for item in items:
                    item_id = item["item_id"]
                    print(f"🖼️  Processing: {item_id}")
                    
                    # Mark as processing
                    integration.mark_item_processing(item_id)
                    
                    # Simulate description generation
                    description = f"Test description for {item_id}"
                    
                    # Mark as completed
                    integration.mark_item_completed(
                        item_id, description, processing_time_ms=1000
                    )
                    
                    total_processed += 1
                    print(f"✅ Completed: {item_id}")
            
            # Get statistics
            stats = integration.get_processing_statistics()
            print(f"\n📊 Processing Statistics:")
            print(f"   Total files: {stats['workflow_progress']['total_files']}")
            print(f"   Completed: {stats['workflow_progress']['completed_files']}")
            print(f"   Failed: {stats['workflow_progress']['failed_files']}")
            
            # Test HTML export
            html_path = test_dir / "test_report.html"
            print(f"\n📄 Generating HTML report...")
            if export_html_from_idw(idw_path, html_path):
                print(f"✅ HTML report generated: {html_path}")
                print(f"   Size: {html_path.stat().st_size} bytes")
            else:
                print(f"❌ Failed to generate HTML report")
                return False
            
            integration.close()
            
            print(f"\n🎉 IDW workflow test completed successfully!")
            print(f"   Processed {total_processed} items")
            print(f"   IDW file: {idw_path} ({idw_path.stat().st_size} bytes)")
            print(f"   HTML report: {html_path}")
            
            return True
            
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    success = test_idw_workflow()
    sys.exit(0 if success else 1)