#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for IDW Manager

Comprehensive test suite covering:
- Basic IDW operations (create, read, update)
- Thread safety and concurrent access
- Atomic operations and corruption recovery
- Resume functionality
- Live monitoring
- Error handling and edge cases
- Performance with large datasets

Author: Image Description Toolkit
Date: September 16, 2025
"""

import unittest
import tempfile
import shutil
import json
import threading
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
import os

# Add scripts directory to path for imports
sys.path.append(str(Path(__file__).parent.parent / "scripts"))

from idw_manager import (
    IDWManager, IDWItem, ProcessingInfo, UserModifications, ItemMetadata,
    ProcessingStatus, ProcessingMode, IDWFormatError, IDWCorruptionError, IDWLockError
)


class TestIDWManager(unittest.TestCase):
    """Test suite for IDWManager class"""
    
    def setUp(self):
        """Set up test environment before each test"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.idw_path = self.test_dir / "test.idw"
        
    def tearDown(self):
        """Clean up test environment after each test"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_create_new_idw_file(self):
        """Test creating a new IDW file"""
        manager = IDWManager(self.idw_path, mode="write")
        
        # File should be created
        self.assertTrue(self.idw_path.exists())
        
        # Should have valid structure
        with open(self.idw_path, 'r') as f:
            data = json.load(f)
        
        self.assertIn("workspace_info", data)
        self.assertIn("workflow_progress", data)
        self.assertIn("processing_config", data)
        self.assertIn("items", data)
        self.assertIn("batch_statistics", data)
        
        # Version should be 2.0
        self.assertEqual(data["workspace_info"]["version"], "2.0")
        
        manager.close()
    
    def test_add_item(self):
        """Test adding items to IDW file"""
        manager = IDWManager(self.idw_path, mode="write")
        
        # Create test item
        item = IDWItem(
            item_id="test_item",
            original_file="/path/to/original.jpg",
            display_file="/path/to/display.jpg",
            description="Test description"
        )
        
        # Add item
        result = manager.add_item(item)
        self.assertTrue(result)
        
        # Verify item was added
        data = manager._load_idw_data()
        self.assertIn("test_item", data["items"])
        
        item_data = data["items"]["test_item"]
        self.assertEqual(item_data["original_file"], "/path/to/original.jpg")
        self.assertEqual(item_data["display_file"], "/path/to/display.jpg")
        self.assertEqual(item_data["description"], "Test description")
        
        # Total files should be updated
        self.assertEqual(data["workflow_progress"]["total_files"], 1)
        
        manager.close()
    
    def test_mark_completed(self):
        """Test marking items as completed"""
        manager = IDWManager(self.idw_path, mode="write")
        
        # Add item first
        item = IDWItem(
            item_id="test_item",
            original_file="/path/to/original.jpg",
            display_file="/path/to/display.jpg"
        )
        manager.add_item(item)
        
        # Mark as completed
        result = manager.mark_completed(
            "test_item", 
            "Generated description",
            processing_time_ms=1500
        )
        self.assertTrue(result)
        
        # Verify completion
        data = manager._load_idw_data()
        item_data = data["items"]["test_item"]
        
        self.assertEqual(item_data["description"], "Generated description")
        self.assertEqual(item_data["processing_info"]["status"], ProcessingStatus.COMPLETED.value)
        self.assertEqual(item_data["processing_info"]["processing_time_ms"], 1500)
        self.assertIsNotNone(item_data["processing_info"]["processed_at"])
        
        # Progress should be updated
        self.assertEqual(data["workflow_progress"]["completed_files"], 1)
        self.assertEqual(data["workflow_progress"]["last_processed"], "test_item")
        
        manager.close()
    
    def test_mark_failed(self):
        """Test marking items as failed"""
        manager = IDWManager(self.idw_path, mode="write")
        
        # Add item first
        item = IDWItem(
            item_id="test_item",
            original_file="/path/to/original.jpg",
            display_file="/path/to/display.jpg"
        )
        manager.add_item(item)
        
        # Mark as failed
        result = manager.mark_failed("test_item", "Connection timeout")
        self.assertTrue(result)
        
        # Verify failure
        data = manager._load_idw_data()
        item_data = data["items"]["test_item"]
        
        self.assertEqual(item_data["processing_info"]["status"], ProcessingStatus.FAILED.value)
        self.assertEqual(item_data["processing_info"]["error_message"], "Connection timeout")
        
        # Progress should be updated
        self.assertEqual(data["workflow_progress"]["failed_files"], 1)
        
        # Error statistics should be updated
        self.assertIn("timeout", data["batch_statistics"]["errors"])
        self.assertEqual(data["batch_statistics"]["errors"]["timeout"], 1)
        
        manager.close()
    
    def test_resume_checkpoint(self):
        """Test resume checkpoint functionality"""
        manager = IDWManager(self.idw_path, mode="write")
        
        # Add multiple items
        for i in range(5):
            item = IDWItem(
                item_id=f"item_{i}",
                original_file=f"/path/to/item_{i}.jpg",
                display_file=f"/path/to/display_{i}.jpg"
            )
            manager.add_item(item)
        
        # Mark some as completed
        manager.mark_completed("item_0", "Description 0")
        manager.mark_completed("item_1", "Description 1")
        
        # Mark one as failed
        manager.mark_failed("item_2", "Test error")
        
        # Get resume checkpoint (should be item_3)
        checkpoint = manager.get_resume_checkpoint()
        self.assertEqual(checkpoint, "item_3")
        
        # Get remaining items
        remaining = manager.get_remaining_items()
        self.assertEqual(set(remaining), {"item_3", "item_4"})
        
        manager.close()
    
    def test_thread_safety(self):
        """Test thread-safe operations"""
        manager = IDWManager(self.idw_path, mode="write")
        
        # Add initial item
        item = IDWItem(
            item_id="test_item",
            original_file="/path/to/original.jpg",
            display_file="/path/to/display.jpg"
        )
        manager.add_item(item)
        
        results = []
        errors = []
        
        def worker_thread(thread_id):
            try:
                # Each thread tries to mark as completed
                result = manager.mark_completed(
                    "test_item", 
                    f"Description from thread {thread_id}",
                    processing_time_ms=1000 + thread_id
                )
                results.append((thread_id, result))
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker_thread, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Should have no errors
        self.assertEqual(len(errors), 0, f"Thread errors: {errors}")
        
        # All operations should succeed (last one wins)
        self.assertEqual(len(results), 5)
        self.assertTrue(all(result for _, result in results))
        
        # Verify final state is consistent
        data = manager._load_idw_data()
        self.assertEqual(data["workflow_progress"]["completed_files"], 1)
        
        manager.close()
    
    def test_corruption_recovery(self):
        """Test recovery from corrupted IDW files"""
        manager = IDWManager(self.idw_path, mode="write")
        
        # Add some data
        item = IDWItem(
            item_id="test_item",
            original_file="/path/to/original.jpg",
            display_file="/path/to/display.jpg",
            description="Test description"
        )
        manager.add_item(item)
        
        # Force another save to create backup
        item2 = IDWItem(
            item_id="test_item2",
            original_file="/path/to/original2.jpg",
            display_file="/path/to/display2.jpg",
            description="Test description 2"
        )
        manager.add_item(item2)
        manager.close()
        
        # Verify backup was created
        backup_path = self.idw_path.with_suffix('.bak')
        self.assertTrue(backup_path.exists())
        
        # Corrupt the main file
        with open(self.idw_path, 'w') as f:
            f.write("invalid json content {")
        
        # Try to load - should recover from backup
        manager2 = IDWManager(self.idw_path, mode="read")
        data = manager2._load_idw_data()
        
        # Should have recovered data
        self.assertIn("test_item", data["items"])
        self.assertEqual(data["items"]["test_item"]["description"], "Test description")
        
        manager2.close()
    
    def test_file_locking(self):
        """Test file locking mechanism"""
        manager1 = IDWManager(self.idw_path, mode="write")
        
        # Add initial data
        item = IDWItem(
            item_id="test_item",
            original_file="/path/to/original.jpg",
            display_file="/path/to/display.jpg"
        )
        manager1.add_item(item)
        
        # Try to create another manager in write mode
        # This should work since we're not actively writing
        manager2 = IDWManager(self.idw_path, mode="write")
        
        # Both should be able to read
        data1 = manager1._load_idw_data()
        data2 = manager2._load_idw_data()
        
        self.assertEqual(data1["items"], data2["items"])
        
        manager1.close()
        manager2.close()
    
    def test_live_monitoring(self):
        """Test live monitoring functionality"""
        manager = IDWManager(self.idw_path, mode="write")
        
        # Set up monitoring
        change_notifications = []
        
        def on_change(changed_items):
            change_notifications.append(changed_items)
        
        manager.add_change_callback(on_change)
        
        # Add item - should trigger notification
        item = IDWItem(
            item_id="test_item",
            original_file="/path/to/original.jpg",
            display_file="/path/to/display.jpg"
        )
        manager.add_item(item)
        
        # Verify notification was sent
        self.assertEqual(len(change_notifications), 1)
        self.assertIn("test_item", change_notifications[0])
        
        # Mark as completed - should trigger another notification
        manager.mark_completed("test_item", "Test description")
        
        self.assertEqual(len(change_notifications), 2)
        self.assertIn("test_item", change_notifications[1])
        
        manager.close()
    
    def test_statistics_tracking(self):
        """Test processing statistics tracking"""
        manager = IDWManager(self.idw_path, mode="write")
        
        # Add and complete multiple items with different processing times
        processing_times = [1000, 1500, 800, 2000, 1200]
        
        for i, time_ms in enumerate(processing_times):
            item = IDWItem(
                item_id=f"item_{i}",
                original_file=f"/path/to/item_{i}.jpg",
                display_file=f"/path/to/display_{i}.jpg"
            )
            manager.add_item(item)
            manager.mark_completed(f"item_{i}", f"Description {i}", processing_time_ms=time_ms)
        
        # Get statistics
        stats = manager.get_statistics()
        
        # Verify statistics
        self.assertEqual(stats["workflow_progress"]["completed_files"], 5)
        self.assertEqual(stats["workflow_progress"]["total_files"], 5)
        
        processing_stats = stats["batch_statistics"]["processing_times"]
        self.assertEqual(processing_stats["fastest_ms"], min(processing_times))
        self.assertEqual(processing_stats["slowest_ms"], max(processing_times))
        
        # Average should be approximately correct
        expected_avg = sum(processing_times) // len(processing_times)
        self.assertAlmostEqual(processing_stats["average_ms"], expected_avg, delta=50)
        
        manager.close()
    
    def test_read_only_mode(self):
        """Test read-only mode restrictions"""
        # Create IDW file first
        manager_write = IDWManager(self.idw_path, mode="write")
        item = IDWItem(
            item_id="test_item",
            original_file="/path/to/original.jpg",
            display_file="/path/to/display.jpg"
        )
        manager_write.add_item(item)
        manager_write.close()
        
        # Open in read-only mode
        manager_read = IDWManager(self.idw_path, mode="read")
        
        # Should be able to read data
        data = manager_read._load_idw_data()
        self.assertIn("test_item", data["items"])
        
        # Should not be able to modify
        with self.assertRaises(PermissionError):
            manager_read.add_item(item)
        
        manager_read.close()
    
    def test_validation_errors(self):
        """Test IDW format validation"""
        # Create invalid IDW file
        invalid_data = {"invalid": "structure"}
        
        with open(self.idw_path, 'w') as f:
            json.dump(invalid_data, f)
        
        # Should raise format error
        manager = IDWManager(self.idw_path, mode="read")
        with self.assertRaises(IDWFormatError):
            manager._load_idw_data()
        
        manager.close()
    
    def test_missing_file_handling(self):
        """Test handling of missing IDW files"""
        # Try to open non-existent file in read mode
        with self.assertRaises(FileNotFoundError):
            manager = IDWManager(self.idw_path, mode="read")
            manager._load_idw_data()  # This should trigger the FileNotFoundError
        
        # Write mode should create the file
        manager = IDWManager(self.idw_path, mode="write")
        self.assertTrue(self.idw_path.exists())
        manager.close()
    
    def test_large_dataset_performance(self):
        """Test performance with large number of items"""
        manager = IDWManager(self.idw_path, mode="write")
        
        start_time = time.time()
        
        # Add 1000 items
        for i in range(1000):
            item = IDWItem(
                item_id=f"item_{i:04d}",
                original_file=f"/path/to/item_{i:04d}.jpg",
                display_file=f"/path/to/display_{i:04d}.jpg"
            )
            manager.add_item(item)
        
        add_time = time.time() - start_time
        
        # Mark 500 as completed
        start_time = time.time()
        for i in range(500):
            manager.mark_completed(f"item_{i:04d}", f"Description {i}")
        
        complete_time = time.time() - start_time
        
        # Performance should be reasonable (adjust thresholds as needed)
        self.assertLess(add_time, 30.0, f"Adding 1000 items took {add_time:.2f}s")
        self.assertLess(complete_time, 30.0, f"Completing 500 items took {complete_time:.2f}s")
        
        # Verify final state
        remaining = manager.get_remaining_items()
        self.assertEqual(len(remaining), 500)
        
        stats = manager.get_statistics()
        self.assertEqual(stats["workflow_progress"]["total_files"], 1000)
        self.assertEqual(stats["workflow_progress"]["completed_files"], 500)
        
        manager.close()
    
    def test_error_categorization(self):
        """Test error message categorization"""
        manager = IDWManager(self.idw_path, mode="write")
        
        # Add test items
        for i in range(5):
            item = IDWItem(
                item_id=f"item_{i}",
                original_file=f"/path/to/item_{i}.jpg",
                display_file=f"/path/to/display_{i}.jpg"
            )
            manager.add_item(item)
        
        # Test different error types
        error_tests = [
            ("Connection timeout occurred", "timeout"),
            ("Out of memory error", "memory"),
            ("File not found: missing.jpg", "file_not_found"),
            ("Permission denied", "permission"),
            ("Unknown error type", "unknown")
        ]
        
        for i, (error_msg, expected_category) in enumerate(error_tests):
            manager.mark_failed(f"item_{i}", error_msg)
        
        # Verify error categorization
        data = manager._load_idw_data()
        errors = data["batch_statistics"]["errors"]
        
        for _, expected_category in error_tests:
            self.assertIn(expected_category, errors)
            self.assertEqual(errors[expected_category], 1)
        
        manager.close()


class TestIDWManagerIntegration(unittest.TestCase):
    """Integration tests for IDWManager with realistic workflows"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.idw_path = self.test_dir / "integration_test.idw"
    
    def tearDown(self):
        """Clean up test environment"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_batch_processing_simulation(self):
        """Simulate a realistic batch processing workflow"""
        manager = IDWManager(self.idw_path, mode="write")
        
        # Simulate discovering 50 files
        files = [f"image_{i:03d}.jpg" for i in range(50)]
        
        # Add all files to IDW
        for file_name in files:
            item = IDWItem(
                item_id=file_name.replace('.', '_'),
                original_file=f"/source/{file_name}",
                display_file=f"/processed/{file_name}"
            )
            manager.add_item(item)
        
        # Simulate processing with some failures
        for i, file_name in enumerate(files):
            item_id = file_name.replace('.', '_')
            
            if i % 10 == 9:  # Every 10th file fails
                manager.mark_failed(item_id, "Simulated processing error")
            else:
                processing_time = 1000 + (i * 100)  # Varying processing times
                manager.mark_completed(item_id, f"Generated description for {file_name}", 
                                     processing_time_ms=processing_time)
        
        # Verify final state
        stats = manager.get_statistics()
        
        self.assertEqual(stats["workflow_progress"]["total_files"], 50)
        self.assertEqual(stats["workflow_progress"]["completed_files"], 45)  # 50 - 5 failures
        self.assertEqual(stats["workflow_progress"]["failed_files"], 5)
        
        # Verify no items need processing
        remaining = manager.get_remaining_items()
        self.assertEqual(len(remaining), 0)
        
        manager.close()
    
    def test_resume_workflow_simulation(self):
        """Simulate a resume workflow after interruption"""
        # First session - process some files
        manager1 = IDWManager(self.idw_path, mode="write")
        
        files = [f"image_{i:03d}.jpg" for i in range(20)]
        
        # Add all files
        for file_name in files:
            item = IDWItem(
                item_id=file_name.replace('.', '_'),
                original_file=f"/source/{file_name}",
                display_file=f"/processed/{file_name}"
            )
            manager1.add_item(item)
        
        # Process first 10 files
        for i in range(10):
            file_name = files[i]
            item_id = file_name.replace('.', '_')
            manager1.mark_completed(item_id, f"Description for {file_name}")
        
        manager1.close()
        
        # Second session - resume processing
        manager2 = IDWManager(self.idw_path, mode="write")
        
        # Get resume checkpoint
        checkpoint = manager2.get_resume_checkpoint()
        self.assertIsNotNone(checkpoint)
        
        # Get remaining work
        remaining = manager2.get_remaining_items()
        self.assertEqual(len(remaining), 10)  # Should have 10 files left
        
        # Complete remaining files
        for item_id in remaining:
            manager2.mark_completed(item_id, f"Description for {item_id}")
        
        # Verify complete state
        final_remaining = manager2.get_remaining_items()
        self.assertEqual(len(final_remaining), 0)
        
        stats = manager2.get_statistics()
        self.assertEqual(stats["workflow_progress"]["completed_files"], 20)
        
        manager2.close()


if __name__ == '__main__':
    # Configure logging for tests
    import logging
    logging.basicConfig(level=logging.WARNING)
    
    # Run tests
    unittest.main(verbosity=2)