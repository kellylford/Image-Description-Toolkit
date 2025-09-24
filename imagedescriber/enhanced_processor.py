#!/usr/bin/env python3
"""
Enhanced Image Processing with Ollama Cloud Support

This script provides enhanced image processing capabilities including:
- Batch processing of hundreds of images
- Automatic HEIC conversion
- Cloud model vision capability detection
- Fallback to local models when cloud vision fails
"""

import os
import json
import base64
import requests
from pathlib import Path
from PIL import Image
import pillow_heif
from typing import List, Dict, Optional
import time

# Register HEIF opener
pillow_heif.register_heif_opener()

class EnhancedImageProcessor:
    """Enhanced image processor with cloud model support and fallbacks"""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.timeout = 300
        self.vision_capable_models = set()  # Cache of models that can see images
        self.non_vision_models = set()      # Cache of models that can't see images
        
    def test_vision_capability(self, model: str) -> bool:
        """Test if a model can actually process images"""
        if model in self.vision_capable_models:
            return True
        if model in self.non_vision_models:
            return False
            
        # Create a simple test image
        test_img = Image.new('RGB', (50, 50), color='red')
        test_data = self._image_to_base64(test_img)
        
        # Test with both API formats
        for api_format in ['openai', 'native']:
            try:
                if api_format == 'openai':
                    response = self._call_openai_api(model, "What color is this image?", test_data)
                else:
                    response = self._call_native_api(model, "What color is this image?", test_data)
                
                # Check if response indicates vision capability
                if response and "red" in response.lower() and not any(
                    indicator in response.lower() 
                    for indicator in ["can't see", "can't view", "unable to see", "no image"]
                ):
                    self.vision_capable_models.add(model)
                    return True
                    
            except Exception:
                continue
                
        self.non_vision_models.add(model)
        return False
    
    def _image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string"""
        import io
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=95)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    def _call_openai_api(self, model: str, prompt: str, image_data: str) -> Optional[str]:
        """Call Ollama using OpenAI-compatible API"""
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                    ]
                }
            ],
            "max_tokens": 500
        }
        
        response = requests.post(
            f"{self.base_url}/v1/chat/completions",
            headers={'Content-Type': 'application/json'},
            json=payload,
            timeout=self.timeout
        )
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        return None
    
    def _call_native_api(self, model: str, prompt: str, image_data: str) -> Optional[str]:
        """Call Ollama using native API"""
        payload = {
            "model": model,
            "prompt": prompt,
            "images": [image_data],
            "stream": False
        }
        
        response = requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=self.timeout
        )
        
        if response.status_code == 200:
            return response.json().get('response')
        return None
    
    def convert_image(self, image_path: Path) -> Path:
        """Convert image to JPEG if needed"""
        if image_path.suffix.lower() in ['.heic', '.heif']:
            # Convert HEIC to JPEG
            output_path = image_path.with_suffix('.jpg')
            try:
                image = Image.open(image_path)
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                image.save(output_path, 'JPEG', quality=95)
                return output_path
            except Exception as e:
                print(f"Failed to convert {image_path}: {e}")
                return image_path
        return image_path
    
    def process_image(self, image_path: Path, prompt: str, preferred_model: str) -> Dict:
        """Process a single image with fallback logic"""
        # Convert if needed
        converted_path = self.convert_image(image_path)
        
        try:
            # Load and encode image
            with open(converted_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            # Try preferred model first
            if self.test_vision_capability(preferred_model):
                result = self._call_openai_api(preferred_model, prompt, image_data)
                if result:
                    return {
                        'success': True,
                        'model_used': preferred_model,
                        'description': result,
                        'image_path': str(image_path),
                        'converted_path': str(converted_path) if converted_path != image_path else None
                    }
            
            # Fallback to local vision models
            local_vision_models = ['llava:latest', 'llava-llama3:latest', 'bakllava:latest', 'moondream:latest']
            for fallback_model in local_vision_models:
                try:
                    if self.test_vision_capability(fallback_model):
                        result = self._call_native_api(fallback_model, prompt, image_data)
                        if result:
                            return {
                                'success': True,
                                'model_used': fallback_model,
                                'description': result,
                                'image_path': str(image_path),
                                'converted_path': str(converted_path) if converted_path != image_path else None,
                                'fallback_used': True,
                                'original_model': preferred_model
                            }
                except Exception:
                    continue
                    
            return {
                'success': False,
                'error': f'No vision-capable models available (tried {preferred_model} and local models)',
                'image_path': str(image_path)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'image_path': str(image_path)
            }
    
    def batch_process(self, images_dir: Path, output_file: Path, prompt: str = "Describe this image in detail.", preferred_model: str = "gpt-oss:120b-cloud"):
        """Process all images in a directory"""
        results = []
        image_extensions = {'.jpg', '.jpeg', '.png', '.heic', '.heif', '.webp'}
        
        # Find all images
        image_files = []
        for ext in image_extensions:
            image_files.extend(images_dir.rglob(f'*{ext}'))
            image_files.extend(images_dir.rglob(f'*{ext.upper()}'))
        
        print(f"Found {len(image_files)} images to process")
        
        for i, image_path in enumerate(image_files, 1):
            print(f"Processing {i}/{len(image_files)}: {image_path.name}")
            
            result = self.process_image(image_path, prompt, preferred_model)
            results.append(result)
            
            # Save progress periodically
            if i % 10 == 0:
                with open(output_file, 'w') as f:
                    json.dump(results, f, indent=2)
                print(f"Saved progress: {i} images processed")
        
        # Final save
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Print summary
        successful = sum(1 for r in results if r.get('success'))
        failed = len(results) - successful
        fallbacks = sum(1 for r in results if r.get('fallback_used'))
        
        print(f"\nProcessing complete!")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Used fallback models: {fallbacks}")
        
        return results

def main():
    """Test the enhanced processor"""
    processor = EnhancedImageProcessor()
    
    # Test cloud model vision capability
    print("Testing cloud model vision capabilities...")
    cloud_models = ['gpt-oss:120b-cloud', 'qwen3-coder:480b-cloud', 'deepseek-v3.1:671b-cloud']
    
    for model in cloud_models:
        can_see = processor.test_vision_capability(model)
        print(f"{model}: {'✅ Vision capable' if can_see else '❌ No vision support'}")
    
    print(f"\nVision-capable models: {processor.vision_capable_models}")
    print(f"Non-vision models: {processor.non_vision_models}")

if __name__ == "__main__":
    main()