#!/usr/bin/env python3
"""
Basic test suite for ImageDescriber application
This will help prevent regressions during refactoring
"""

import unittest
import sys
import os
from pathlib import Path

# Add the imagedescriber directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QPixmap
    import imagedescriber
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please ensure PyQt6 and all dependencies are installed")
    sys.exit(1)


class TestImageWorkspace(unittest.TestCase):
    """Test the ImageWorkspace class functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.workspace = imagedescriber.ImageWorkspace(new_workspace=True)
    
    def test_workspace_creation(self):
        """Test that workspace can be created"""
        self.assertIsNotNone(self.workspace)
        self.assertIsInstance(self.workspace.items, dict)
        self.assertEqual(len(self.workspace.items), 0)
    
    def test_workspace_modification_tracking(self):
        """Test that workspace properly tracks modifications"""
        # Initially should be saved
        self.assertTrue(self.workspace.saved)
        
        # After marking modified, should be unsaved
        self.workspace.mark_modified()
        self.assertFalse(self.workspace.saved)
    
    def test_add_item(self):
        """Test adding items to workspace"""
        test_path = "/test/path/image.jpg"
        item = imagedescriber.ImageItem(test_path, "image")
        
        self.workspace.add_item(item)
        self.assertEqual(len(self.workspace.items), 1)
        self.assertIn(test_path, self.workspace.items)
        self.assertFalse(self.workspace.saved)  # Should be marked as modified


class TestImageItem(unittest.TestCase):
    """Test the ImageItem class functionality"""
    
    def test_image_item_creation(self):
        """Test that ImageItem can be created"""
        test_path = "/test/path/image.jpg"
        item = imagedescriber.ImageItem(test_path, "image")
        
        self.assertEqual(item.file_path, test_path)
        self.assertEqual(item.item_type, "image")
        self.assertEqual(len(item.descriptions), 0)
        self.assertFalse(item.batch_marked)
    
    def test_add_description(self):
        """Test adding descriptions to an item"""
        item = imagedescriber.ImageItem("/test/path/image.jpg", "image")
        description = imagedescriber.ImageDescription(
            text="Test description",
            model="test-model",
            provider="test-provider"
        )
        
        item.add_description(description)
        self.assertEqual(len(item.descriptions), 1)
        self.assertEqual(item.descriptions[0].text, "Test description")


class TestAIProviders(unittest.TestCase):
    """Test AI provider functionality"""
    
    def test_provider_availability(self):
        """Test that we can check provider availability"""
        providers = imagedescriber.get_available_providers()
        self.assertIsInstance(providers, dict)
        self.assertTrue(len(providers) > 0)  # Should have at least one provider
        
        # Test that we have some providers available (configuration dependent)
        available_names = list(providers.keys())
        print(f"Available providers: {available_names}")
        
        # Should have at least ollama or huggingface (these don't require API keys)
        self.assertTrue(any(name in available_names for name in ['ollama', 'huggingface']))
    
    def test_ollama_provider_creation(self):
        """Test that Ollama provider can be created"""
        provider = imagedescriber.OllamaProvider()
        self.assertEqual(provider.get_provider_name(), "Ollama")
        
    def test_openai_provider_creation(self):
        """Test that OpenAI provider can be created"""
        provider = imagedescriber.OpenAIProvider()
        self.assertEqual(provider.get_provider_name(), "OpenAI")


class TestApplicationBasics(unittest.TestCase):
    """Test basic application functionality"""
    
    @classmethod
    def setUpClass(cls):
        """Set up QApplication for GUI tests"""
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()
    
    def test_gui_creation(self):
        """Test that the main GUI can be created"""
        try:
            gui = imagedescriber.ImageDescriberGUI()
            self.assertIsNotNone(gui)
            gui.close()
        except Exception as e:
            self.fail(f"Failed to create GUI: {e}")
    
    def test_workspace_operations(self):
        """Test basic workspace operations don't crash"""
        try:
            gui = imagedescriber.ImageDescriberGUI()
            
            # Test new workspace
            gui.new_workspace()
            self.assertIsNotNone(gui.workspace)
            
            gui.close()
        except Exception as e:
            self.fail(f"Workspace operations failed: {e}")


class TestUtilityFunctions(unittest.TestCase):
    """Test utility functions"""
    
    def test_configuration_loading(self):
        """Test that configuration can be loaded"""
        # This tests the load_prompt_config functionality
        worker = imagedescriber.ProcessingWorker("test.jpg", "ollama", "test-model", "detailed")
        config = worker.load_prompt_config()
        
        self.assertIsInstance(config, dict)
        self.assertIn("prompts", config)


def run_tests():
    """Run all tests and return success status"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestImageWorkspace,
        TestImageItem,
        TestAIProviders,
        TestApplicationBasics,
        TestUtilityFunctions
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return success status
    return result.wasSuccessful()


if __name__ == "__main__":
    print("Running ImageDescriber Basic Test Suite")
    print("=" * 50)
    
    success = run_tests()
    
    print("\n" + "=" * 50)
    if success:
        print("SUCCESS: All tests passed!")
        sys.exit(0)
    else:
        print("FAILED: Some tests failed!")
        sys.exit(1)