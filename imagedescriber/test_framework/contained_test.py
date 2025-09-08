#!/usr/bin/env python3
"""
Properly contained test framework for ImageDescriber
All files and outputs stay within imagedescriber/test_framework/
"""

import base64
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

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

class ContainedImageTester:
    """Contained test class that mirrors ImageDescriber functionality"""
    
    def __init__(self):
        self.test_dir = TEST_DIR
        self.models = self.detect_available_models()
        self.prompts = {
            'detailed': 'Provide a detailed description of this image.',
            'brief': 'Briefly describe this image.',
            'creative': 'Describe this image in a creative, engaging way.'
        }
        self.results = []
        
        # Create output subdirectory
        self.output_dir = self.test_dir / "results"
        self.output_dir.mkdir(exist_ok=True)
        
        print(f"✓ Test framework contained in: {self.test_dir}")
        print(f"✓ Results will be saved to: {self.output_dir}")
    
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
            return available_models
            
        except Exception as e:
            print(f"Model detection failed: {e}")
            return ['moondream', 'gemma3', 'llava']
        
    def get_test_images(self) -> List[Path]:
        """Get list of test images"""
        if not TEST_IMAGES_DIR.exists():
            print(f"✗ Test directory not found: {TEST_IMAGES_DIR}")
            return []
        
        # Get JPG and PNG files (avoid HEIC issues)
        images = []
        for ext in ['*.jpg', '*.jpeg', '*.png']:
            images.extend(TEST_IMAGES_DIR.glob(ext))
        
        # Limit to 3 images for initial test
        return sorted(images)[:3]
    
    def process_image(self, image_path: Path, model: str, prompt_key: str, prompt_text: str) -> Dict:
        """Process one image with one model and prompt - mirrors ProcessingWorker"""
        try:
            print(f"\n--- Processing {image_path.name} with {model} ({prompt_key}) ---")
            
            # Read and encode image (same as ProcessingWorker)
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
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
            return result
    
    def test_follow_ups(self, original_result: Dict) -> List[Dict]:
        """Test follow-up questions - mirrors what the app does"""
        if original_result['status'] != 'success':
            return []
        
        follow_ups = [
            "What colors are prominent in this image?",
            "What is the mood or atmosphere of this image?",
            "Are there any people or animals in this image?"
        ]
        
        follow_up_results = []
        
        for follow_up in follow_ups[:2]:  # Limit to 2 follow-ups to avoid timeout
            try:
                print(f"\n  Follow-up: {follow_up}")
                
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
                        follow_up_results.append(follow_up_result)
                    else:
                        print(f"  ✗ Follow-up failed: Empty response")
                else:
                    print(f"  ✗ Follow-up failed: Bad response format")
                    
            except Exception as e:
                print(f"  ✗ Follow-up failed: {str(e)}")
        
        return follow_up_results
    
    def run_test(self, max_tests: int = 9):
        """Run the complete test with limits to avoid long runs"""
        print("Contained ImageDescriber Test")
        print("=" * 60)
        
        # Get test images
        images = self.get_test_images()
        if not images:
            print("No test images found!")
            return
        
        print(f"Found {len(images)} test images: {[img.name for img in images]}")
        print(f"Testing models: {self.models}")
        print(f"Testing prompts: {list(self.prompts.keys())}")
        
        # Limit total tests to avoid very long runs
        total_combinations = len(images) * len(self.models) * len(self.prompts)
        if total_combinations > max_tests:
            print(f"Limiting to {max_tests} tests (of {total_combinations} possible)")
        
        current_test = 0
        
        for image in images:
            for model in self.models:
                for prompt_key, prompt_text in self.prompts.items():
                    current_test += 1
                    if current_test > max_tests:
                        print(f"\nReached test limit of {max_tests}")
                        break
                        
                    print(f"\n[{current_test}/{min(max_tests, total_combinations)}] Testing combination...")
                    
                    # Main processing
                    result = self.process_image(image, model, prompt_key, prompt_text)
                    self.results.append(result)
                    
                    # Test follow-ups for successful results (limited)
                    if result['status'] == 'success':
                        follow_ups = self.test_follow_ups(result)
                        self.results.extend(follow_ups)
                
                if current_test >= max_tests:
                    break
            if current_test >= max_tests:
                break
        
        # Save results
        self.save_results()
        self.print_summary()
    
    def save_results(self):
        """Save results to JSON file in the contained directory"""
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        output_file = self.output_dir / f"test_results_{timestamp}.json"
        
        # Create a more readable format
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
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(formatted_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Results saved to {output_file}")
    
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
    tester.run_test(max_tests=9)  # Limit to 9 tests for quick run
