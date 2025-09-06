#!/usr/bin/env python3
"""
Image Describer - Interactive Image Processing GUI

A Qt6-based GUI application for processing images individually or in batches
using the proven workflow scripts. Provides an approachable interface for
generating AI-powered image descriptions without requiring command-line knowledge.

Features:
- Directory-based image browsing
- Individual image processing (P key)
- Batch processing queue (B key to mark, Batch Process button)
- Real-time progress feedback
- HTML output generation
- Integration with existing workflow scripts
"""

import sys
import os
import json
import subprocess
import threading
import time
from pathlib import Path
from typing import List, Set, Optional, Dict

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
    QListWidget, QListWidgetItem, QPushButton, QLabel, 
    QWidget, QFileDialog, QMessageBox, QProgressBar,
    QSplitter, QTextEdit, QGroupBox, QFrame, QTabWidget,
    QScrollArea
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QMutex, QMutexLocker
)
from PyQt6.QtGui import QFont, QPixmap, QIcon, QKeySequence, QShortcut


class ImageProcessor(QThread):
    """Thread for processing images without blocking the UI"""
    
    progress_updated = pyqtSignal(str, str)  # status, details
    processing_complete = pyqtSignal(str, bool)  # image_path, success
    batch_progress = pyqtSignal(int, int, str)  # current, total, current_file
    
    def __init__(self, scripts_dir: Path):
        super().__init__()
        self.scripts_dir = scripts_dir
        self.image_queue: List[str] = []
        self.is_batch_mode = False
        self.mutex = QMutex()
        
    def process_single_image(self, image_path: str):
        """Process a single image"""
        with QMutexLocker(self.mutex):
            self.image_queue = [image_path]
            self.is_batch_mode = False
        self.start()
        
    def process_batch(self, image_paths: List[str]):
        """Process multiple images in batch"""
        with QMutexLocker(self.mutex):
            self.image_queue = image_paths.copy()
            self.is_batch_mode = True
        self.start()
        
    def run(self):
        """Main processing thread"""
        total_images = len(self.image_queue)
        
        for i, image_path in enumerate(self.image_queue, 1):
            if self.is_batch_mode:
                self.batch_progress.emit(i, total_images, os.path.basename(image_path))
            
            try:
                success = self._process_image_file(image_path)
                self.processing_complete.emit(image_path, success)
                
                if not success:
                    self.progress_updated.emit(
                        f"Failed to process {os.path.basename(image_path)}", 
                        "Check logs for details"
                    )
                    
            except Exception as e:
                self.progress_updated.emit(
                    f"Error processing {os.path.basename(image_path)}", 
                    str(e)
                )
                self.processing_complete.emit(image_path, False)
                
        if self.is_batch_mode:
            self.progress_updated.emit("Batch processing complete", f"Processed {total_images} images")
            
    def _process_image_file(self, image_path: str) -> bool:
        """Process a single image file using the workflow scripts"""
        image_path = Path(image_path)
        
        try:
            # Update status
            self.progress_updated.emit(
                f"Processing {image_path.name}", 
                "Preparing image..."
            )
            
            # Use the image in its current location, don't copy to working directory
            working_image_path = image_path
                
            # Determine if image needs conversion
            if image_path.suffix.lower() in ['.heic', '.heif']:
                self.progress_updated.emit(
                    f"Converting {image_path.name}", 
                    "Converting HEIC format..."
                )
                success = self._convert_heic(working_image_path)
                if not success:
                    return False
                    
            # Check if it's a video that needs frame extraction
            elif image_path.suffix.lower() in ['.mp4', '.mov', '.avi', '.mkv']:
                self.progress_updated.emit(
                    f"Extracting frames from {image_path.name}", 
                    "Processing video file..."
                )
                success = self._extract_video_frames(working_image_path)
                if not success:
                    return False
                    
            # Generate description using image_describer
            self.progress_updated.emit(
                f"Generating description for {image_path.name}", 
                "Running AI analysis..."
            )
            success = self._generate_description(working_image_path)
            
            return success
            
        except Exception as e:
            self.progress_updated.emit(f"Error: {str(e)}", "Processing failed")
            return False
            
    def _convert_heic(self, image_path: Path) -> bool:
        """Convert HEIC image using ConvertImage script"""
        try:
            convert_script = self.scripts_dir / "ConvertImage.py"
            # Create a temporary directory with just this image for processing
            import tempfile
            import shutil
            
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                temp_image = temp_path / image_path.name
                shutil.copy2(image_path, temp_image)
                
                self.progress_updated.emit(
                    f"Converting {image_path.name}", 
                    "Processing HEIC conversion..."
                )
                
                cmd = [
                    str(self._get_python_executable()),
                    str(convert_script),
                    str(temp_path)
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(temp_path))
                
                if result.returncode == 0:
                    # Find and copy converted files back
                    for converted_file in temp_path.glob("*"):
                        if (converted_file.suffix.lower() in ['.jpg', '.jpeg', '.png'] and 
                            converted_file.name != image_path.name):
                            target = image_path.parent / converted_file.name
                            shutil.copy2(converted_file, target)
                            self.progress_updated.emit(
                                f"Converted {image_path.name}", 
                                f"Created {converted_file.name}"
                            )
                    return True
                else:
                    self.progress_updated.emit(
                        f"Failed to convert {image_path.name}", 
                        result.stderr or "Conversion failed"
                    )
                    return False
                    
        except Exception as e:
            self.progress_updated.emit(
                f"Error converting {image_path.name}", 
                str(e)
            )
            return False
            
    def _extract_video_frames(self, video_path: Path) -> bool:
        """Extract frames from video using video_frame_extractor script"""
        try:
            extractor_script = self.scripts_dir / "video_frame_extractor.py"
            # Create a temporary directory with just this video for processing
            import tempfile
            import shutil
            
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                temp_video = temp_path / video_path.name
                shutil.copy2(video_path, temp_video)
                
                self.progress_updated.emit(
                    f"Extracting frames from {video_path.name}", 
                    "Processing video file..."
                )
                
                cmd = [
                    str(self._get_python_executable()),
                    str(extractor_script),
                    str(temp_path)
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(temp_path))
                
                if result.returncode == 0:
                    # Find and copy extracted frames back
                    for frame_file in temp_path.glob("*"):
                        if (frame_file.suffix.lower() in ['.jpg', '.jpeg', '.png'] and 
                            frame_file.name != video_path.name):
                            target = video_path.parent / frame_file.name
                            shutil.copy2(frame_file, target)
                            self.progress_updated.emit(
                                f"Extracted frame from {video_path.name}", 
                                f"Created {frame_file.name}"
                            )
                    return True
                else:
                    self.progress_updated.emit(
                        f"Failed to extract frames from {video_path.name}", 
                        result.stderr or "Frame extraction failed"
                    )
                    return False
                    
        except Exception as e:
            self.progress_updated.emit(
                f"Error extracting frames from {video_path.name}", 
                str(e)
            )
            return False
            
    def _generate_description(self, image_path: Path) -> bool:
        """Generate description using image_describer script"""
        try:
            describer_script = self.scripts_dir / "image_describer.py"
            # Create a temporary directory with just this image for processing
            import tempfile
            import shutil
            
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                temp_image = temp_path / image_path.name
                shutil.copy2(image_path, temp_image)
                
                self.progress_updated.emit(
                    f"Generating description for {image_path.name}", 
                    "Running AI analysis..."
                )
                
                cmd = [
                    str(self._get_python_executable()),
                    str(describer_script),
                    str(temp_path)
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(temp_path))
                
                if result.returncode == 0:
                    # Find and copy description file back
                    desc_file = temp_path / f"{image_path.stem}.txt"
                    if desc_file.exists():
                        target_desc = image_path.parent / f"{image_path.stem}.txt"
                        shutil.copy2(desc_file, target_desc)
                        self.progress_updated.emit(
                            f"Generated description for {image_path.name}", 
                            f"Created {target_desc.name}"
                        )
                        return True
                    else:
                        # Look for any .txt files created
                        txt_files = list(temp_path.glob("*.txt"))
                        if txt_files:
                            target_desc = image_path.parent / f"{image_path.stem}.txt"
                            shutil.copy2(txt_files[0], target_desc)
                            self.progress_updated.emit(
                                f"Generated description for {image_path.name}", 
                                f"Created {target_desc.name}"
                            )
                            return True
                        else:
                            self.progress_updated.emit(
                                f"No description file generated for {image_path.name}", 
                                "AI processing may have failed"
                            )
                            return False
                else:
                    self.progress_updated.emit(
                        f"Failed to generate description for {image_path.name}", 
                        result.stderr or "AI processing failed"
                    )
                    return False
                    
        except Exception as e:
            self.progress_updated.emit(
                f"Error generating description for {image_path.name}", 
                str(e)
            )
            return False
            
    def _get_python_executable(self) -> Path:
        """Get the Python executable path"""
        # Try to use the same Python executable as the current process
        python_exe = Path(sys.executable)
        if python_exe.exists():
            return python_exe
        return Path("python")


class ImageDescriberGUI(QMainWindow):
    """Main GUI application for image processing"""
    
    def __init__(self):
        super().__init__()
        
        # Application state
        self.working_directory: Optional[Path] = None
        self.image_files: List[Path] = []
        self.batch_queue: Set[str] = set()
        self.processed_images: Set[str] = set()
        self.scripts_directory = self._get_scripts_directory()
        
        # UI components
        self.image_list: Optional[QListWidget] = None
        self.status_label: Optional[QLabel] = None
        self.progress_bar: Optional[QProgressBar] = None
        self.batch_button: Optional[QPushButton] = None
        self.finalize_button: Optional[QPushButton] = None
        self.log_text: Optional[QTextEdit] = None
        self.description_tabs: Optional[QTabWidget] = None
        self.description_text: Optional[QTextEdit] = None
        self.copy_button: Optional[QPushButton] = None
        self.redescribe_button: Optional[QPushButton] = None
        
        # Processing
        self.processor: Optional[ImageProcessor] = None
        
        self._setup_ui()
        self._setup_shortcuts()
        self._update_window_title()
        
    def _get_scripts_directory(self) -> Path:
        """Get the scripts directory path"""
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            bundle_dir = Path(sys._MEIPASS)
            return bundle_dir / 'scripts'
        else:
            # Running as script
            current_dir = Path(__file__).parent
            return current_dir.parent / 'scripts'
            
    def _setup_ui(self):
        """Setup the user interface"""
        self.setWindowTitle("Image Describer")
        self.setMinimumSize(800, 600)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Directory selection
        dir_layout = QHBoxLayout()
        dir_button = QPushButton("Select Image Directory")
        dir_button.clicked.connect(self._select_directory)
        self.status_label = QLabel("No directory selected")
        dir_layout.addWidget(dir_button)
        dir_layout.addWidget(self.status_label, 1)
        main_layout.addLayout(dir_layout)
        
        # Splitter for main content
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel - Image list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Image list
        list_group = QGroupBox("Images")
        list_layout = QVBoxLayout(list_group)
        
        self.image_list = QListWidget()
        self.image_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.image_list.itemSelectionChanged.connect(self._on_selection_changed)
        list_layout.addWidget(self.image_list)
        
        # Instructions
        instructions = QLabel(
            "Instructions:\n"
            "• Press P to process selected image\n"
            "• Press B to mark for batch processing\n"
            "• Press Tab to switch between Description/Log\n"
            "• Use Copy/Redescribe buttons after processing\n"
            "• Use Batch Process button for queued items"
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("QLabel { background-color: #f0f0f0; padding: 5px; }")
        list_layout.addWidget(instructions)
        
        left_layout.addWidget(list_group)
        
        # Control buttons
        button_layout = QVBoxLayout()
        
        self.batch_button = QPushButton("Batch Process (0 queued)")
        self.batch_button.clicked.connect(self._process_batch)
        self.batch_button.setEnabled(False)
        button_layout.addWidget(self.batch_button)
        
        self.finalize_button = QPushButton("Finalize & Generate HTML")
        self.finalize_button.clicked.connect(self._finalize_processing)
        self.finalize_button.setEnabled(False)
        button_layout.addWidget(self.finalize_button)
        
        left_layout.addLayout(button_layout)
        splitter.addWidget(left_panel)
        
        # Right panel - Progress and logs
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Description tabs (like viewer)
        self.description_tabs = QTabWidget()
        
        # Description tab
        desc_widget = QWidget()
        desc_layout = QVBoxLayout(desc_widget)
        
        self.description_text = QTextEdit()
        self.description_text.setReadOnly(True)
        self.description_text.setPlainText("Select and process an image to see its description...")
        desc_layout.addWidget(self.description_text)
        
        # Description controls
        desc_controls = QHBoxLayout()
        self.copy_button = QPushButton("Copy Description")
        self.copy_button.clicked.connect(self._copy_description)
        self.copy_button.setEnabled(False)
        
        self.redescribe_button = QPushButton("Redescribe")
        self.redescribe_button.clicked.connect(self._redescribe_image)
        self.redescribe_button.setEnabled(False)
        
        desc_controls.addWidget(self.copy_button)
        desc_controls.addWidget(self.redescribe_button)
        desc_controls.addStretch()
        desc_layout.addLayout(desc_controls)
        
        self.description_tabs.addTab(desc_widget, "Description")
        
        # Progress section
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        # Log section
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        log_layout.addWidget(self.log_text)
        
        self.description_tabs.addTab(log_widget, "Processing Log")
        
        right_layout.addWidget(progress_group)
        right_layout.addWidget(self.description_tabs)
        
        splitter.addWidget(right_panel)
        
        # Set splitter proportions
        splitter.setSizes([400, 400])
        
    def _setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        # Process selected image (P key)
        process_shortcut = QShortcut(QKeySequence("P"), self)
        process_shortcut.activated.connect(self._process_selected_image)
        
        # Mark for batch (B key)
        batch_shortcut = QShortcut(QKeySequence("B"), self)
        batch_shortcut.activated.connect(self._mark_for_batch)
        
        # Tab key to switch between description and log
        tab_shortcut = QShortcut(QKeySequence("Tab"), self)
        tab_shortcut.activated.connect(self._switch_tab)
        
    def _select_directory(self):
        """Select working directory containing images"""
        directory = QFileDialog.getExistingDirectory(
            self, 
            "Select Directory Containing Images",
            str(Path.home())
        )
        
        if directory:
            self.working_directory = Path(directory)
            self._load_images()
            self._update_window_title()
            
    def _load_images(self):
        """Load images from the selected directory"""
        if not self.working_directory:
            return
            
        # Supported image and video extensions
        supported_extensions = {
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif',
            '.heic', '.heif', '.webp', '.mp4', '.mov', '.avi', '.mkv'
        }
        
        self.image_files = []
        self.image_list.clear()
        
        # Find all supported files
        for file_path in self.working_directory.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                self.image_files.append(file_path)
                
        # Sort files by name
        self.image_files.sort(key=lambda x: x.name.lower())
        
        # Add to list widget
        for image_path in self.image_files:
            item = QListWidgetItem(image_path.name)
            item.setData(Qt.ItemDataRole.UserRole, str(image_path))
            
            # Check if already processed
            if str(image_path) in self.processed_images:
                item.setBackground(Qt.GlobalColor.lightGray)
                
            # Check if in batch queue
            if str(image_path) in self.batch_queue:
                item.setBackground(Qt.GlobalColor.yellow)
                
            self.image_list.addItem(item)
            
        self.status_label.setText(f"Loaded {len(self.image_files)} files from {self.working_directory.name}")
        self._log(f"Loaded {len(self.image_files)} files from {self.working_directory}")
        
    def _on_selection_changed(self):
        """Handle image selection change"""
        current_item = self.image_list.currentItem()
        if current_item:
            image_path = current_item.data(Qt.ItemDataRole.UserRole)
            self._load_description_for_image(image_path)
            
    def _load_description_for_image(self, image_path: str):
        """Load and display description for the selected image"""
        image_path = Path(image_path)
        
        # Look for description file
        desc_file = image_path.with_suffix('.txt')
        
        if desc_file.exists():
            try:
                with open(desc_file, 'r', encoding='utf-8') as f:
                    description = f.read().strip()
                self.description_text.setPlainText(description)
                self.copy_button.setEnabled(True)
                self.redescribe_button.setEnabled(True)
            except Exception as e:
                self.description_text.setPlainText(f"Error reading description: {str(e)}")
                self.copy_button.setEnabled(False)
                self.redescribe_button.setEnabled(False)
        else:
            self.description_text.setPlainText("No description found. Press P to process this image.")
            self.copy_button.setEnabled(False)
            self.redescribe_button.setEnabled(False)
        
    def _process_selected_image(self):
        """Process the currently selected image"""
        current_item = self.image_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select an image to process.")
            return
            
        image_path = current_item.data(Qt.ItemDataRole.UserRole)
        self._log(f"Starting individual processing: {Path(image_path).name}")
        
        # Setup processor if needed
        if not self.processor:
            self.processor = ImageProcessor(self.scripts_directory)
            self.processor.progress_updated.connect(self._on_progress_updated)
            self.processor.processing_complete.connect(self._on_processing_complete)
            
        # Start processing
        self.processor.process_single_image(image_path)
        self._show_progress("Processing image...")
        
    def _mark_for_batch(self):
        """Mark the selected image for batch processing"""
        current_item = self.image_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select an image to mark for batch processing.")
            return
            
        image_path = current_item.data(Qt.ItemDataRole.UserRole)
        
        if image_path in self.batch_queue:
            # Remove from batch queue
            self.batch_queue.remove(image_path)
            current_item.setBackground(Qt.GlobalColor.white)
            self._log(f"Removed from batch queue: {Path(image_path).name}")
        else:
            # Add to batch queue
            self.batch_queue.add(image_path)
            current_item.setBackground(Qt.GlobalColor.yellow)
            self._log(f"Added to batch queue: {Path(image_path).name}")
            
        # Update batch button
        queue_count = len(self.batch_queue)
        self.batch_button.setText(f"Batch Process ({queue_count} queued)")
        self.batch_button.setEnabled(queue_count > 0)
        
    def _process_batch(self):
        """Process all images in the batch queue"""
        if not self.batch_queue:
            return
            
        batch_list = list(self.batch_queue)
        self._log(f"Starting batch processing: {len(batch_list)} images")
        
        # Setup processor if needed
        if not self.processor:
            self.processor = ImageProcessor(self.scripts_directory)
            self.processor.progress_updated.connect(self._on_progress_updated)
            self.processor.processing_complete.connect(self._on_processing_complete)
            self.processor.batch_progress.connect(self._on_batch_progress)
            
        # Start batch processing
        self.processor.process_batch(batch_list)
        self._show_progress("Batch processing...")
        
        # Clear batch queue and update UI
        self.batch_queue.clear()
        self.batch_button.setText("Batch Process (0 queued)")
        self.batch_button.setEnabled(False)
        
    def _finalize_processing(self):
        """Generate HTML output from processed descriptions"""
        if not self.working_directory:
            return
            
        try:
            self._log("Generating HTML output...")
            
            # Use the descriptions_to_html script
            html_script = self.scripts_directory / "descriptions_to_html.py"
            cmd = [
                str(self.processor._get_python_executable() if self.processor else "python"),
                str(html_script),
                str(self.working_directory)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.working_directory))
            
            if result.returncode == 0:
                self._log("HTML output generated successfully!")
                QMessageBox.information(
                    self, 
                    "Success", 
                    f"HTML output has been generated in:\n{self.working_directory}"
                )
            else:
                self._log(f"HTML generation failed: {result.stderr}")
                QMessageBox.warning(
                    self, 
                    "HTML Generation Failed", 
                    f"Failed to generate HTML output:\n{result.stderr}"
                )
                
        except Exception as e:
            self._log(f"Error during HTML generation: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error during HTML generation:\n{str(e)}")
            
    def _show_progress(self, message: str):
        """Show progress bar with message"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.setWindowTitle(f"Image Describer - {message}")
        
    def _hide_progress(self):
        """Hide progress bar"""
        self.progress_bar.setVisible(False)
        self._update_window_title()
        
    def _on_progress_updated(self, status: str, details: str):
        """Handle progress updates from processor"""
        self.setWindowTitle(f"Image Describer - {status}")
        self._log(f"{status}: {details}")
        
    def _on_processing_complete(self, image_path: str, success: bool):
        """Handle completion of image processing"""
        image_name = Path(image_path).name
        
        if success:
            self.processed_images.add(image_path)
            self._log(f"✓ Successfully processed: {image_name}")
            
            # Update UI - mark as processed
            for i in range(self.image_list.count()):
                item = self.image_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == image_path:
                    item.setBackground(Qt.GlobalColor.lightGray)
                    break
                    
            # Enable finalize button
            self.finalize_button.setEnabled(True)
        else:
            self._log(f"✗ Failed to process: {image_name}")
            
        # Remove from batch queue if it was there
        self.batch_queue.discard(image_path)
        
        # Refresh the description display if this image is currently selected
        current_item = self.image_list.currentItem()
        if current_item and current_item.data(Qt.ItemDataRole.UserRole) == image_path:
            self._load_description_for_image(image_path)
        
        self._hide_progress()
        
    def _copy_description(self):
        """Copy the current description to clipboard"""
        description = self.description_text.toPlainText()
        if description and description.strip():
            app = QApplication.instance()
            app.clipboard().setText(description)
            self._log("Description copied to clipboard")
            
    def _redescribe_image(self):
        """Redescribe the currently selected image"""
        current_item = self.image_list.currentItem()
        if not current_item:
            return
            
        image_path = current_item.data(Qt.ItemDataRole.UserRole)
        
        # Delete existing description file
        desc_file = Path(image_path).with_suffix('.txt')
        if desc_file.exists():
            desc_file.unlink()
            
        # Process the image again
        self._process_selected_image()
        
    def _switch_tab(self):
        """Switch between Description and Log tabs using Tab key"""
        if self.description_tabs:
            current_index = self.description_tabs.currentIndex()
            next_index = (current_index + 1) % self.description_tabs.count()
            self.description_tabs.setCurrentIndex(next_index)
        
    def _on_batch_progress(self, current: int, total: int, current_file: str):
        """Handle batch progress updates"""
        self.setWindowTitle(f"Image Describer - Batch Processing ({current}/{total}): {current_file}")
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(current)
        
    def _log(self, message: str):
        """Add message to processing log"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        
        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def _update_window_title(self):
        """Update the main window title"""
        if self.working_directory:
            self.setWindowTitle(f"Image Describer - {self.working_directory.name}")
        else:
            self.setWindowTitle("Image Describer")


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Image Describer")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Image Description Toolkit")
    
    # Create and show main window
    window = ImageDescriberGUI()
    window.show()
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
