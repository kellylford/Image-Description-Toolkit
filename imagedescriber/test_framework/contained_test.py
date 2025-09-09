#!/usr/bin/env python3
"""
Properly contained test framework for ImageDescriber
All files and outputs stay within imagedescriber/test_framework/
"""

import base64
import json
import sys
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Setup paths properly - this test lives in imagedescriber/test_framework/
TEST_DIR = Path(__file__).parent
REPO_ROOT = TEST_DIR.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
TEST_IMAGES_DIR = REPO_ROOT / "tests" / "test_files" / "images"

# Add scripts directory for ollama import
sys.path.insert(0, str(SCRIPTS_DIR))

try:
    import ollama
    print("✓ Ollama imported")
except ImportError as e:
    print(f"✗ Failed to import ollama: {e}")
    sys.exit(1)

# ImageDescriber constants and classes (copied from app)
WORKSPACE_VERSION = "1.0"

class ImageDescription:
    """Represents a single description for an image"""
    def __init__(self, text: str, model: str = "", prompt_style: str = "", 
                 created: str = "", custom_prompt: str = ""):
        self.text = text
        self.model = model
        self.prompt_style = prompt_style
        self.created = created or datetime.now().isoformat()
        self.custom_prompt = custom_prompt
        self.id = f"{int(time.time() * 1000)}"  # Unique ID
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "model": self.model,
            "prompt_style": self.prompt_style,
            "created": self.created,
            "custom_prompt": self.custom_prompt
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        desc = cls(
            text=data.get("text", ""),
            model=data.get("model", ""),
            prompt_style=data.get("prompt_style", ""),
            created=data.get("created", ""),
            custom_prompt=data.get("custom_prompt", "")
        )
        desc.id = data.get("id", desc.id)
        return desc

class ImageItem:
    """Represents an image in the workspace - EXACT copy from the app"""
    def __init__(self, file_path: str, item_type: str = "image"):
        self.file_path = file_path
        self.item_type = item_type  # "image", "video", "extracted_frame"
        self.descriptions: List[ImageDescription] = []
        self.batch_marked = False
        self.parent_video = None  # For extracted frames
        self.extracted_frames: List[str] = []  # For videos
        
    def add_description(self, description: ImageDescription):
        self.descriptions.append(description)
    
    def remove_description(self, desc_id: str):
        self.descriptions = [d for d in self.descriptions if d.id != desc_id]
    
    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "item_type": self.item_type,
            "descriptions": [d.to_dict() for d in self.descriptions],
            "batch_marked": self.batch_marked,
            "parent_video": self.parent_video,
            "extracted_frames": self.extracted_frames
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        item = cls(data["file_path"], data.get("item_type", "image"))
        item.descriptions = [ImageDescription.from_dict(d) for d in data.get("descriptions", [])]
        item.batch_marked = data.get("batch_marked", False)
        item.parent_video = data.get("parent_video")
        item.extracted_frames = data.get("extracted_frames", [])
        return item

class ImageWorkspace:
    """Document model for ImageDescriber workspace - Enhanced for multiple directories"""
    def __init__(self, new_workspace=False):
        self.version = WORKSPACE_VERSION
        # Support both single directory (legacy) and multiple directories
        self.directory_path = ""  # Keep for backward compatibility
        self.directory_paths: List[str] = []  # New: support multiple directories
        self.items: Dict[str, ImageItem] = {}
        self.created = datetime.now().isoformat()
        self.modified = self.created
        self.saved = new_workspace
        
    def add_directory(self, directory_path: str):
        """Add a directory to the workspace"""
        abs_path = str(Path(directory_path).resolve())
        if abs_path not in self.directory_paths:
            self.directory_paths.append(abs_path)
            self.mark_modified()
            
        # Update legacy field for compatibility
        if not self.directory_path:
            self.directory_path = abs_path
    
    def get_all_directories(self) -> List[str]:
        """Get all directories in workspace"""
        dirs = []
        if self.directory_path and self.directory_path not in dirs:
            dirs.append(self.directory_path)
        dirs.extend([d for d in self.directory_paths if d not in dirs])
        return dirs
        
    def add_item(self, item: ImageItem):
        self.items[item.file_path] = item
        self.mark_modified()
    
    def remove_item(self, file_path: str):
        if file_path in self.items:
            del self.items[file_path]
            self.mark_modified()
    
    def get_item(self, file_path: str):
        return self.items.get(file_path)
    
    def mark_modified(self):
        self.modified = datetime.now().isoformat()
        self.saved = False
    
    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "directory_path": self.directory_path,  # Legacy compatibility
            "directory_paths": self.directory_paths,  # New multi-directory support
            "items": {path: item.to_dict() for path, item in self.items.items()},
            "created": self.created,
            "modified": self.modified
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        workspace = cls()
        workspace.version = data.get("version", WORKSPACE_VERSION)
        workspace.directory_path = data.get("directory_path", "")
        workspace.directory_paths = data.get("directory_paths", [])
        workspace.items = {path: ImageItem.from_dict(item_data) 
                          for path, item_data in data.get("items", {}).items()}
        workspace.created = data.get("created", workspace.created)
        workspace.modified = data.get("modified", workspace.modified)
        workspace.saved = True
        return workspace

class ContainedImageTester:
    """Contained test class that mirrors ImageDescriber functionality"""
    
    def __init__(self):
        self.test_dir = TEST_DIR
        self.models = self.detect_available_models()
        
        # Load REAL prompts from the app's config file
        self.prompts = self.load_real_prompts()
        
        self.results = []
        
        # Create output subdirectory
        self.output_dir = self.test_dir / "results"
        self.output_dir.mkdir(exist_ok=True)
        
        # Create workspace like the app does
        self.workspace = ImageWorkspace(new_workspace=True)
        self.workspace.add_directory(str(TEST_IMAGES_DIR))  # Use new multi-directory support
        
        # Setup single workspace file for this test run
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        self.workspace_file = self.output_dir / f"test_workspace_{timestamp}.idw"
        
        # Setup logging like the app does
        self.setup_logging()
        
        print(f"✓ Test framework contained in: {self.test_dir}")
        print(f"✓ Results will be saved to: {self.output_dir}")
        print(f"✓ Workspace created for directory: {self.workspace.directory_path}")
        print(f"✓ Workspace file: {self.workspace_file}")
        print(f"✓ Loaded {len(self.prompts)} REAL prompts from app config: {list(self.prompts.keys())}")
    
    def load_real_prompts(self) -> Dict[str, str]:
        """Load the REAL prompts from the ImageDescriber app config"""
        try:
            config_path = SCRIPTS_DIR / "image_describer_config.json"
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # Get the actual prompt variations from the config
                prompt_variations = config.get("prompt_variations", {})
                print(f"✓ Loaded prompts from app config: {list(prompt_variations.keys())}")
                return prompt_variations
            else:
                print(f"✗ Config file not found: {config_path}")
        except Exception as e:
            print(f"✗ Failed to load app config: {e}")
        
        # Fallback to default if config fails
        return {
            "Narrative": "Provide a narrative description including objects, colors and detail. Avoid interpretation, just describe."
        }
    
    def setup_logging(self):
        """Setup logging to file like the app does"""
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        self.log_file = self.output_dir / f"test_log_{timestamp}.txt"
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file, encoding='utf-8'),
                logging.StreamHandler()  # Also log to console
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("="*60)
        self.logger.info("Starting ImageDescriber Test Session")
        self.logger.info(f"Test directory: {self.test_dir}")
        self.logger.info(f"Output directory: {self.output_dir}")
        self.logger.info(f"Log file: {self.log_file}")
        self.logger.info("="*60)
    
    def detect_available_models(self) -> List[str]:
        """Detect available Ollama models - mirrors ImageDescriber app logic"""
        try:
            models_response = ollama.list()
            available_models = []
            
            if 'models' in models_response:
                for model in models_response['models']:
                    model_name = model.get('name', '')
                    if model_name:
                        available_models.append(model_name)
            
            if not available_models:
                available_models = ['moondream', 'gemma3', 'llava']
            
            print(f"✓ Detected models: {available_models}")
            if hasattr(self, 'logger'):
                self.logger.info(f"Detected {len(available_models)} models: {available_models}")
            return available_models
            
        except Exception as e:
            print(f"Model detection failed: {e}")
            if hasattr(self, 'logger'):
                self.logger.error(f"Model detection failed: {e}")
            return ['moondream', 'gemma3', 'llava']
        
    def get_test_images(self, recursive: bool = False, max_images: int = 3) -> List[Path]:
        """Get list of test images with optional recursive search
        
        Args:
            recursive: If True, search subdirectories recursively
            max_images: Maximum number of images to return (0 = no limit)
        """
        if not TEST_IMAGES_DIR.exists():
            print(f"✗ Test directory not found: {TEST_IMAGES_DIR}")
            return []
        
        # Get JPG and PNG files (avoid HEIC issues)
        images = []
        for ext in ['*.jpg', '*.jpeg', '*.png']:
            if recursive:
                # Use ** for recursive glob pattern
                images.extend(TEST_IMAGES_DIR.rglob(ext))
                print(f"✓ Recursive search for {ext}: found {len(list(TEST_IMAGES_DIR.rglob(ext)))} files")
            else:
                # Use single * for current directory only
                images.extend(TEST_IMAGES_DIR.glob(ext))
        
        sorted_images = sorted(images)
        
        if recursive and sorted_images:
            print(f"✓ Found {len(sorted_images)} total images across all subdirectories")
            # Show directory breakdown
            dirs = {}
            for img in sorted_images:
                parent = str(img.parent.relative_to(TEST_IMAGES_DIR))
                if parent == '.':
                    parent = 'root'
                dirs[parent] = dirs.get(parent, 0) + 1
            
            for dir_name, count in dirs.items():
                print(f"  - {dir_name}: {count} images")
        
        # Apply limit if specified
        if max_images > 0:
            return sorted_images[:max_images]
        return sorted_images
    
    def process_image(self, image_path: Path, model: str, prompt_key: str, prompt_text: str) -> Dict:
        """Process one image with one model and prompt - mirrors ProcessingWorker"""
        try:
            print(f"\n--- Processing {image_path.name} with {model} ({prompt_key}) ---")
            self.logger.info(f"Processing {image_path.name} with model {model} ({prompt_key})")
            self.logger.info(f"Prompt: {prompt_text}")
            
            # Read and encode image (same as ProcessingWorker)
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            self.logger.info(f"Image size: {len(image_data)} bytes")
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Call Ollama (same as ProcessingWorker)
            start_time = time.time()
            response = ollama.chat(
                model=model,
                messages=[{
                    'role': 'user',
                    'content': prompt_text,
                    'images': [image_base64]
                }],
                options={
                    'temperature': 0.1,
                    'num_predict': 600
                }
            )
            end_time = time.time()
            
            # Extract response (same as ProcessingWorker)
            if 'message' in response and 'content' in response['message']:
                content = response['message']['content']
                if content and content.strip():
                    # Create description and add to workspace like the app does
                    description = ImageDescription(
                        text=content.strip(),
                        model=model,
                        prompt_style=prompt_key,
                        custom_prompt=prompt_text if prompt_key == "custom" else ""
                    )
                    
                    # Add to workspace like the app does
                    image_key = str(image_path)
                    if image_key not in self.workspace.items:
                        self.workspace.add_item(ImageItem(image_key))
                    
                    self.workspace.get_item(image_key).add_description(description)
                    
                    result = {
                        'image': image_path.name,
                        'model': model,
                        'prompt_key': prompt_key,
                        'prompt_text': prompt_text,
                        'description': content.strip(),
                        'processing_time': round(end_time - start_time, 2),
                        'status': 'success'
                    }
                    
                    print(f"✓ SUCCESS ({result['processing_time']}s)")
                    print(f"Description: {content.strip()[:100]}...")
                    self.logger.info(f"SUCCESS: {result['processing_time']}s")
                    self.logger.info(f"Description: {content.strip()}")
                    
                    return result
                else:
                    raise Exception("Empty response from model")
            else:
                raise Exception(f"Unexpected response format: {response}")
                
        except Exception as e:
            result = {
                'image': image_path.name,
                'model': model,
                'prompt_key': prompt_key,
                'prompt_text': prompt_text,
                'description': f"ERROR: {str(e)}",
                'processing_time': 0,
                'status': 'failed'
            }
            print(f"✗ FAILED: {str(e)}")
            self.logger.error(f"FAILED: {str(e)}")
            return result
    
    def test_follow_ups(self, original_result: Dict) -> List[Dict]:
        """Test follow-up questions - mirrors what the app does"""
        if original_result['status'] != 'success':
            return []
        
        # Realistic follow-up questions that would actually be asked
        follow_ups = [
            "What specific objects can you identify in this image?",
            "Describe the lighting and color scheme in more detail."
        ]
        
        follow_up_results = []
        
        for follow_up in follow_ups:
            try:
                print(f"\n  Follow-up: {follow_up}")
                self.logger.info(f"Follow-up question: {follow_up}")
                
                # Read image again
                image_path = TEST_IMAGES_DIR / original_result['image']
                with open(image_path, 'rb') as f:
                    image_data = f.read()
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                
                # Call with follow-up
                start_time = time.time()
                response = ollama.chat(
                    model=original_result['model'],
                    messages=[{
                        'role': 'user',
                        'content': follow_up,
                        'images': [image_base64]
                    }],
                    options={
                        'temperature': 0.1,
                        'num_predict': 200  # Shorter responses for follow-ups
                    }
                )
                end_time = time.time()
                
                if 'message' in response and 'content' in response['message']:
                    content = response['message']['content']
                    if content and content.strip():
                        follow_up_result = {
                            'image': original_result['image'],
                            'model': original_result['model'],
                            'prompt_key': f"follow_up",
                            'prompt_text': follow_up,
                            'description': content.strip(),
                            'processing_time': round(end_time - start_time, 2),
                            'status': 'success'
                        }
                        print(f"  ✓ Follow-up SUCCESS ({follow_up_result['processing_time']}s)")
                        print(f"  Answer: {content.strip()[:80]}...")
                        self.logger.info(f"Follow-up SUCCESS: {follow_up_result['processing_time']}s")
                        self.logger.info(f"Follow-up answer: {content.strip()}")
                        follow_up_results.append(follow_up_result)
                    else:
                        print(f"  ✗ Follow-up failed: Empty response")
                        self.logger.warning(f"Follow-up failed: Empty response for '{follow_up}'")
                else:
                    print(f"  ✗ Follow-up failed: Bad response format")
                    self.logger.warning(f"Follow-up failed: Bad response format for '{follow_up}'")
                    
            except Exception as e:
                print(f"  ✗ Follow-up failed: {str(e)}")
                self.logger.error(f"Follow-up failed: {str(e)} for '{follow_up}'")
        
        return follow_up_results
    
    def run_test(self, max_tests: int = None, recursive: bool = False, max_images: int = 3):
        """Run the comprehensive test suite
        
        Args:
            max_tests: Maximum number of test combinations to run (None = no limit)
            recursive: If True, search for images recursively in subdirectories
            max_images: Maximum number of images to test (0 = no limit)
        """
        print("Contained ImageDescriber Test")
        print("=" * 60)
        self.logger.info("Starting test run")
        
        # Get test images with optional recursive search
        images = self.get_test_images(recursive=recursive, max_images=max_images)
        if not images:
            print("No test images found!")
            self.logger.error("No test images found!")
            return
        
        # Use ALL prompts from the app config
        prompt_subset = self.prompts
        
        print(f"Found {len(images)} test images: {[img.name for img in images]}")
        print(f"Testing models: {self.models}")
        print(f"Testing prompts: {list(prompt_subset.keys())}")
        if recursive:
            print(f"✓ Using recursive directory search")
        else:
            print(f"✓ Using single directory search")
        
        self.logger.info(f"Found {len(images)} test images: {[img.name for img in images]}")
        self.logger.info(f"Testing models: {self.models}")
        self.logger.info(f"Testing prompts: {list(prompt_subset.keys())}")
        self.logger.info(f"Recursive search: {recursive}")
        
        # Calculate total tests
        total_combinations = len(images) * len(self.models) * len(prompt_subset)
        if max_tests and total_combinations > max_tests:
            print(f"Limiting to {max_tests} tests (of {total_combinations} possible)")
            self.logger.info(f"Limiting to {max_tests} tests (of {total_combinations} possible)")
        else:
            print(f"Running all {total_combinations} test combinations")
            self.logger.info(f"Running all {total_combinations} test combinations")
        
        current_test = 0
        
        for image in images:
            for model in self.models:
                for prompt_key, prompt_text in prompt_subset.items():
                    current_test += 1
                    if max_tests and current_test > max_tests:
                        print(f"\nReached test limit of {max_tests}")
                        self.logger.info(f"Reached test limit of {max_tests}")
                        break
                        
                    total_to_show = min(max_tests, total_combinations) if max_tests else total_combinations
                    print(f"\n[{current_test}/{total_to_show}] Testing combination...")
                    self.logger.info(f"Test {current_test}/{total_to_show}: {image.name} + {model} + {prompt_key}")
                    
                    # Main processing
                    result = self.process_image(image, model, prompt_key, prompt_text)
                    self.results.append(result)
                    
                    # Save workspace incrementally like the app does after successful processing
                    if result['status'] == 'success':
                        self.save_workspace_incremental()
                    
                    # Test follow-ups for successful results (limited)
                    if result['status'] == 'success':
                        follow_ups = self.test_follow_ups(result)
                        self.results.extend(follow_ups)
                
                if max_tests and current_test >= max_tests:
                    break
            if max_tests and current_test >= max_tests:
                break
        
        # Final save
        self.logger.info("Test run completed, saving final results")
        self.save_results()
        self.print_summary()
    
    def save_results(self):
        """Save results to JSON file and workspace to .idw file in the contained directory"""
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        
        # Save JSON results
        results_file = self.output_dir / f"test_results_{timestamp}.json"
        formatted_results = {
            'test_info': {
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'total_tests': len(self.results),
                'models_tested': self.models,
                'prompts_tested': list(self.prompts.keys()),
                'output_directory': str(self.output_dir)
            },
            'results': self.results
        }
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(formatted_results, f, indent=2, ensure_ascii=False)
        
        # Final save of workspace to the same file (no new file)
        self.save_workspace_to_file()
        
        print(f"\n✓ Results saved to {results_file}")
        print(f"✓ Workspace saved to {self.workspace_file}")
        self.logger.info(f"Results saved to {results_file}")
        self.logger.info(f"Final workspace saved to {self.workspace_file}")
    
    def save_workspace_to_file(self):
        """Save workspace to the single workspace file (like the app does)"""
        try:
            with open(self.workspace_file, 'w', encoding='utf-8') as f:
                json.dump(self.workspace.to_dict(), f, indent=2)
            
            self.workspace.saved = True
            self.logger.info(f"Workspace updated: {self.workspace_file}")
            
        except Exception as e:
            print(f"✗ Failed to save workspace: {e}")
            self.logger.error(f"Failed to save workspace: {e}")
    
    def save_workspace_incremental(self):
        """Save workspace incrementally like the app does after each description"""
        # Update the SAME workspace file, don't create new ones
        self.save_workspace_to_file()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        successful = [r for r in self.results if r['status'] == 'success']
        failed = [r for r in self.results if r['status'] == 'failed']
        
        print(f"Total tests: {len(self.results)}")
        print(f"Successful: {len(successful)}")
        print(f"Failed: {len(failed)}")
        
        if successful:
            avg_time = sum(r['processing_time'] for r in successful) / len(successful)
            print(f"Average processing time: {avg_time:.2f}s")
        
        # Summary by model
        print("\nBy Model:")
        for model in self.models:
            model_results = [r for r in self.results if r['model'] == model]
            model_success = [r for r in model_results if r['status'] == 'success']
            print(f"  {model}: {len(model_success)}/{len(model_results)} successful")
        
        if failed:
            print("\nFailures:")
            for failure in failed[:3]:  # Show first 3 failures
                print(f"  {failure['image']} + {failure['model']}: {failure['description']}")

if __name__ == "__main__":
    tester = ContainedImageTester()
    tester.run_test()  # Run all tests with real prompts from the app
