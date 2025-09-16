#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workflow IDW Integration

Integration functions for using IDWManager with the workflow processing system.
Provides batch processing, resume functionality, and live monitoring capabilities.

Author: Image Description Toolkit
Date: September 16, 2025
"""

import sys
import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone

# Add scripts directory to path for imports
sys.path.append(str(Path(__file__).parent))

from idw_manager import (
    IDWManager, IDWItem, ProcessingInfo, ItemMetadata, UserModifications,
    ProcessingStatus, ProcessingMode
)
from workflow_utils import FileDiscovery, WorkflowConfig

logger = logging.getLogger(__name__)


class WorkflowIDWIntegration:
    """
    Integration layer between workflow processing and IDWManager
    
    Provides:
    - Batch processing with IDW output
    - Resume capability from IDW files
    - Progress tracking and statistics
    - Original file preservation
    """
    
    def __init__(self, idw_path: Path, processing_config: Dict[str, Any]):
        """
        Initialize workflow IDW integration
        
        Args:
            idw_path: Path to IDW file
            processing_config: Configuration for processing (model, prompt, etc.)
        """
        self.idw_path = idw_path
        self.processing_config = processing_config
        
        # Create a minimal workflow config for file discovery
        self.workflow_config = WorkflowConfig()
        self.discovery = FileDiscovery(self.workflow_config)
        self.idw_manager = None
        
    def initialize_batch_processing(self, input_dir: Path, resume: bool = False) -> Dict[str, Any]:
        """
        Initialize batch processing with IDW output
        
        Args:
            input_dir: Input directory to process
            resume: Whether to resume from existing IDW file
            
        Returns:
            Dictionary with initialization results
        """
        try:
            # Open IDW manager in write mode
            self.idw_manager = IDWManager(self.idw_path, mode="write")
            
            if resume and self.idw_path.exists():
                logger.info(f"Resuming batch processing from: {self.idw_path}")
                return self._setup_resume_processing(input_dir)
            else:
                logger.info(f"Starting new batch processing to: {self.idw_path}")
                return self._setup_new_processing(input_dir)
                
        except Exception as e:
            logger.error(f"Failed to initialize batch processing: {e}")
            raise
    
    def _setup_new_processing(self, input_dir: Path) -> Dict[str, Any]:
        """Setup new batch processing"""
        # Discover all files to process
        image_files = self.discovery.find_files_by_type(input_dir, "images")
        video_files = self.discovery.find_files_by_type(input_dir, "videos")
        
        # Create batch ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_id = f"batch_{timestamp}"
        
        # Initialize workspace info
        data = self.idw_manager._load_idw_data()
        data["workspace_info"].update({
            "source_directory": str(input_dir),
            "processing_mode": ProcessingMode.BATCH.value
        })
        data["workflow_progress"].update({
            "batch_id": batch_id,
            "total_files": len(image_files) + len(video_files)
        })
        data["processing_config"].update(self.processing_config)
        
        # Add all discovered files to IDW
        total_added = 0
        
        # Add image files
        for image_file in image_files:
            item_id = self._generate_item_id(image_file)
            item = IDWItem(
                item_id=item_id,
                original_file=str(image_file),
                display_file=str(image_file),  # Initially same as original
                processing_info=ProcessingInfo(
                    status=ProcessingStatus.NOT_STARTED,
                    source_type="image"
                )
            )
            self.idw_manager.add_item(item)
            total_added += 1
        
        # Add video files (these will need frame extraction)
        for video_file in video_files:
            item_id = self._generate_item_id(video_file)
            item = IDWItem(
                item_id=item_id,
                original_file=str(video_file),
                display_file=str(video_file),  # Will be updated after frame extraction
                processing_info=ProcessingInfo(
                    status=ProcessingStatus.NOT_STARTED,
                    source_type="video"
                )
            )
            self.idw_manager.add_item(item)
            total_added += 1
        
        logger.info(f"Added {total_added} files to batch processing")
        
        return {
            "success": True,
            "batch_id": batch_id,
            "total_files": total_added,
            "files_to_process": total_added,
            "mode": "new"
        }
    
    def _setup_resume_processing(self, input_dir: Path) -> Dict[str, Any]:
        """Setup resume processing from existing IDW"""
        # Load existing data
        data = self.idw_manager._load_idw_data()
        
        # Get current progress
        total_files = data["workflow_progress"]["total_files"]
        completed_files = data["workflow_progress"]["completed_files"]
        failed_files = data["workflow_progress"]["failed_files"]
        
        # Get remaining files to process
        remaining_items = self.idw_manager.get_remaining_items()
        
        logger.info(f"Resuming processing: {completed_files}/{total_files} completed, "
                   f"{len(remaining_items)} remaining")
        
        return {
            "success": True,
            "batch_id": data["workflow_progress"]["batch_id"],
            "total_files": total_files,
            "completed_files": completed_files,
            "failed_files": failed_files,
            "files_to_process": len(remaining_items),
            "mode": "resume"
        }
    
    def initialize_from_descriptions(self, input_dir: Path, descriptions_file: Path) -> Dict[str, Any]:
        """
        Initialize IDW from existing descriptions file
        
        Args:
            input_dir: Input directory that was processed
            descriptions_file: Path to existing descriptions file
            
        Returns:
            Dict with initialization results
        """
        logger.info(f"Initializing IDW from descriptions: {descriptions_file}")
        
        # Initialize IDW manager
        self.idw_manager = IDWManager(self.idw_path)
        
        # Generate batch ID
        batch_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        
        # Create workflow metadata
        data = self.idw_manager._load_idw_data()
        data["workflow_progress"] = {
            "batch_id": batch_id,
            "total_files": 0,
            "completed_files": 0,
            "failed_files": 0,
            "start_time": datetime.now(timezone.utc).isoformat(),
            "input_directory": str(input_dir)
        }
        data["processing_config"] = self.processing_config.copy()
        
        # Parse descriptions file to create IDW items
        total_added = 0
        
        try:
            with open(descriptions_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse descriptions - each file section is separated by lines
            # Format: File: <path>\nDescription: <description>\n
            sections = content.split('\n\n')
            
            for section in sections:
                lines = section.strip().split('\n')
                if len(lines) >= 2:
                    # Extract file path and description
                    file_line = lines[0]
                    desc_line = lines[1]
                    
                    if file_line.startswith('File: ') and desc_line.startswith('Description: '):
                        file_path = file_line[6:].strip()  # Remove "File: " prefix
                        description = desc_line[12:].strip()  # Remove "Description: " prefix
                        
                        # Create full path relative to input directory
                        full_path = input_dir / file_path
                        
                        if full_path.exists():
                            item_id = self._generate_item_id(full_path)
                            item = IDWItem(
                                item_id=item_id,
                                original_file=str(full_path),
                                display_file=str(full_path),
                                description=description,
                                processing_info=ProcessingInfo(
                                    status=ProcessingStatus.COMPLETED,
                                    source_type="image",
                                    processed_at=datetime.now(timezone.utc).isoformat()
                                )
                            )
                            self.idw_manager.add_item(item)
                            total_added += 1
                            logger.debug(f"Added completed item: {file_path}")
                        else:
                            logger.warning(f"File not found: {full_path}")
                            
        except Exception as e:
            logger.error(f"Error parsing descriptions file: {e}")
            return {
                "success": False,
                "error": str(e),
                "total_files": 0
            }
        
        # Update progress
        data["workflow_progress"]["total_files"] = total_added
        data["workflow_progress"]["completed_files"] = total_added
        
        # Save the data
        self.idw_manager._save_idw_data(data)
        
        logger.info(f"Successfully initialized IDW with {total_added} completed items")
        
        return {
            "success": True,
            "batch_id": batch_id,
            "total_files": total_added,
            "completed_files": total_added,
            "mode": "from_descriptions"
        }
    
    def get_next_items_to_process(self, batch_size: int = 1) -> List[Dict[str, Any]]:
        """
        Get next items to process
        
        Args:
            batch_size: Number of items to return
            
        Returns:
            List of items to process
        """
        if not self.idw_manager:
            raise RuntimeError("IDW manager not initialized")
        
        remaining_items = self.idw_manager.get_remaining_items()
        items_to_process = remaining_items[:batch_size]
        
        # Load item data
        data = self.idw_manager._load_idw_data()
        result = []
        
        for item_id in items_to_process:
            if item_id in data["items"]:
                item_data = data["items"][item_id]
                result.append({
                    "item_id": item_id,
                    "original_file": item_data["original_file"],
                    "display_file": item_data["display_file"],
                    "source_type": item_data.get("processing_info", {}).get("source_type", "image")
                })
        
        return result
    
    def mark_item_processing(self, item_id: str) -> bool:
        """Mark an item as currently being processed"""
        if not self.idw_manager:
            return False
        
        data = self.idw_manager._load_idw_data()
        if item_id in data["items"]:
            data["items"][item_id]["processing_info"]["status"] = ProcessingStatus.PROCESSING.value
            data["items"][item_id]["processing_info"]["processed_at"] = datetime.now(timezone.utc).isoformat()
            self.idw_manager._save_idw_data(data)
            return True
        return False
    
    def mark_item_completed(self, item_id: str, description: str, 
                           processing_time_ms: Optional[int] = None,
                           display_file: Optional[str] = None,
                           metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Mark an item as completed
        
        Args:
            item_id: Item identifier
            description: Generated description
            processing_time_ms: Processing time in milliseconds
            display_file: Updated display file path (if different from original)
            metadata: Additional metadata
            
        Returns:
            True if successful
        """
        if not self.idw_manager:
            return False
        
        # Update display file if provided
        if display_file:
            data = self.idw_manager._load_idw_data()
            if item_id in data["items"]:
                data["items"][item_id]["display_file"] = display_file
                self.idw_manager._save_idw_data(data)
        
        return self.idw_manager.mark_completed(item_id, description, processing_time_ms, metadata)
    
    def mark_item_failed(self, item_id: str, error_message: str) -> bool:
        """Mark an item as failed"""
        if not self.idw_manager:
            return False
        
        return self.idw_manager.mark_failed(item_id, error_message)
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get current processing statistics"""
        if not self.idw_manager:
            return {}
        
        return self.idw_manager.get_statistics()
    
    def is_processing_complete(self) -> bool:
        """Check if all processing is complete"""
        if not self.idw_manager:
            return False
        
        remaining = self.idw_manager.get_remaining_items()
        return len(remaining) == 0
    
    def update_file_mapping(self, item_id: str, original_file: str, 
                           display_file: str, source_type: str = "image") -> bool:
        """
        Update file mapping for an item (useful for video frame extraction)
        
        Args:
            item_id: Item identifier  
            original_file: Original source file
            display_file: Processed display file
            source_type: Type of source (image, video_frame, converted_heic)
            
        Returns:
            True if successful
        """
        if not self.idw_manager:
            return False
        
        data = self.idw_manager._load_idw_data()
        if item_id in data["items"]:
            data["items"][item_id]["original_file"] = original_file
            data["items"][item_id]["display_file"] = display_file
            data["items"][item_id]["processing_info"]["source_type"] = source_type
            self.idw_manager._save_idw_data(data)
            return True
        return False
    
    def add_extracted_frames(self, video_file: Path, frame_files: List[Path], 
                            extraction_dir: Path) -> List[str]:
        """
        Add extracted video frames to IDW processing
        
        Args:
            video_file: Original video file
            frame_files: List of extracted frame files
            extraction_dir: Directory containing extracted frames
            
        Returns:
            List of new item IDs created for frames
        """
        if not self.idw_manager:
            return []
        
        new_item_ids = []
        
        for frame_file in frame_files:
            # Create item ID for frame
            frame_item_id = self._generate_item_id(frame_file)
            
            # Create IDW item for frame
            item = IDWItem(
                item_id=frame_item_id,
                original_file=str(video_file),  # Original source is the video
                display_file=str(frame_file),   # Display the extracted frame
                processing_info=ProcessingInfo(
                    status=ProcessingStatus.NOT_STARTED,
                    source_type="video_frame",
                    extraction_source=str(video_file)
                )
            )
            
            self.idw_manager.add_item(item)
            new_item_ids.append(frame_item_id)
        
        logger.info(f"Added {len(new_item_ids)} video frames from {video_file.name}")
        return new_item_ids
    
    def _generate_item_id(self, file_path: Path) -> str:
        """Generate a unique item ID from file path"""
        # Use stem (filename without extension) and make it safe for IDs
        stem = file_path.stem
        # Replace any problematic characters
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in stem)
        return safe_id
    
    def close(self):
        """Close the IDW manager"""
        if self.idw_manager:
            self.idw_manager.close()
            self.idw_manager = None


def create_workflow_with_idw(input_dir: Path, idw_path: Path, 
                            processing_config: Dict[str, Any],
                            resume: bool = False,
                            existing_descriptions_file: Optional[Path] = None) -> WorkflowIDWIntegration:
    """
    Create a workflow integration with IDW output
    
    Args:
        input_dir: Input directory to process
        idw_path: Path for IDW output file
        processing_config: Processing configuration
        resume: Whether to resume from existing IDW
        existing_descriptions_file: Path to existing descriptions file to import
        
    Returns:
        WorkflowIDWIntegration instance
    """
    integration = WorkflowIDWIntegration(idw_path, processing_config)
    
    if existing_descriptions_file and existing_descriptions_file.exists():
        # Initialize from existing descriptions
        init_result = integration.initialize_from_descriptions(input_dir, existing_descriptions_file)
    else:
        # Initialize new batch processing
        init_result = integration.initialize_batch_processing(input_dir, resume)
    
    logger.info(f"Workflow IDW integration initialized: {init_result}")
    return integration


def export_html_from_idw(idw_path: Path, output_html_path: Path) -> bool:
    """
    Export HTML report from IDW file
    
    Args:
        idw_path: Path to IDW file
        output_html_path: Path for output HTML file
        
    Returns:
        True if successful
    """
    try:
        manager = IDWManager(idw_path, mode="read")
        data = manager._load_idw_data()
        
        # Generate HTML content
        html_content = _generate_html_report(data)
        
        # Write HTML file
        with open(output_html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        manager.close()
        logger.info(f"HTML report exported to: {output_html_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to export HTML from IDW: {e}")
        return False


def _generate_html_report(data: Dict[str, Any]) -> str:
    """Generate HTML report content from IDW data"""
    
    workspace_info = data.get("workspace_info", {})
    progress = data.get("workflow_progress", {})
    items = data.get("items", {})
    stats = data.get("batch_statistics", {})
    
    # Count items by status
    completed_items = [item for item in items.values() 
                      if item.get("processing_info", {}).get("status") == "completed"]
    failed_items = [item for item in items.values() 
                   if item.get("processing_info", {}).get("status") == "failed"]
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Image Description Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
        .header {{ background: #f4f4f4; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin-bottom: 20px; }}
        .stat-box {{ background: #e9e9e9; padding: 15px; border-radius: 5px; text-align: center; }}
        .item {{ border: 1px solid #ddd; margin-bottom: 20px; padding: 15px; border-radius: 5px; }}
        .item img {{ max-width: 300px; height: auto; float: left; margin-right: 15px; }}
        .item-info {{ overflow: hidden; }}
        .description {{ margin-top: 10px; padding: 10px; background: #f9f9f9; border-radius: 3px; }}
        .failed {{ border-color: #ff6b6b; background: #fff5f5; }}
        .completed {{ border-color: #51cf66; background: #f8fff8; }}
        .clear {{ clear: both; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Image Description Report</h1>
        <p><strong>Generated:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        <p><strong>Source Directory:</strong> {workspace_info.get('source_directory', 'Unknown')}</p>
        <p><strong>Processing Model:</strong> {data.get('processing_config', {}).get('model', 'Unknown')}</p>
        <p><strong>Batch ID:</strong> {progress.get('batch_id', 'Unknown')}</p>
    </div>
    
    <div class="stats">
        <div class="stat-box">
            <h3>Total Files</h3>
            <div>{progress.get('total_files', 0)}</div>
        </div>
        <div class="stat-box">
            <h3>Completed</h3>
            <div>{len(completed_items)}</div>
        </div>
        <div class="stat-box">
            <h3>Failed</h3>
            <div>{len(failed_items)}</div>
        </div>
        <div class="stat-box">
            <h3>Success Rate</h3>
            <div>{(len(completed_items) / max(1, progress.get('total_files', 1)) * 100):.1f}%</div>
        </div>
    </div>
"""
    
    # Add completed items
    if completed_items:
        html += "<h2>Successfully Processed Images</h2>\n"
        for item_id, item_data in items.items():
            if item_data.get("processing_info", {}).get("status") == "completed":
                display_file = item_data.get("display_file", "")
                original_file = item_data.get("original_file", "")
                description = item_data.get("description", "No description available")
                processing_time = item_data.get("processing_info", {}).get("processing_time_ms", 0)
                
                html += f"""
                <div class="item completed">
                    <img src="{display_file}" alt="{item_id}" onerror="this.style.display='none'">
                    <div class="item-info">
                        <h3>{item_id}</h3>
                        <p><strong>Original File:</strong> {original_file}</p>
                        <p><strong>Processing Time:</strong> {processing_time}ms</p>
                        <div class="description">
                            <strong>Description:</strong><br>
                            {description}
                        </div>
                    </div>
                    <div class="clear"></div>
                </div>
                """
    
    # Add failed items
    if failed_items:
        html += "<h2>Failed Items</h2>\n"
        for item_id, item_data in items.items():
            if item_data.get("processing_info", {}).get("status") == "failed":
                original_file = item_data.get("original_file", "")
                error_message = item_data.get("processing_info", {}).get("error_message", "Unknown error")
                
                html += f"""
                <div class="item failed">
                    <div class="item-info">
                        <h3>{item_id}</h3>
                        <p><strong>Original File:</strong> {original_file}</p>
                        <p><strong>Error:</strong> {error_message}</p>
                    </div>
                </div>
                """
    
    html += """
</body>
</html>
"""
    
    return html