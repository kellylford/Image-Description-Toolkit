#!/usr/bin/env python3
"""
OpenAI Model Testing Script
Tests gpt-5-nano issue and validates other OpenAI models

Usage:
    python test_openai_models.py --phase 1  # Model validation (3 images × 4 models)
    python test_openai_models.py --phase 2  # gpt-5-nano baseline (100 images)
    python test_openai_models.py --phase 3  # gpt-5-nano optimized (100 images)
    python test_openai_models.py --all      # Run all phases
"""

import json
import base64
import time
import random
import logging
import argparse
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import Counter

# OpenAI SDK
try:
    from openai import OpenAI
except ImportError:
    print("ERROR: OpenAI Python SDK not installed. Run: pip install openai")
    exit(1)

# PIL for PNG conversion
try:
    from PIL import Image
    import io
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("WARNING: PIL not available, PNG conversion disabled")


class OpenAITester:
    """Test OpenAI models systematically"""
    
    def __init__(self, api_key: str, output_dir: Path):
        self.client = OpenAI(api_key=api_key)
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(output_dir / 'test_run.log'),
                logging.StreamHandler()
            ]
        )
        
        self.results = []
    
    def load_image_sample(self, workspace_path: Path, count: int = 100, 
                         strategy: str = 'random') -> List[Dict[str, Any]]:
        """Load image paths from workspace with selection strategy"""
        
        self.logger.info(f"Loading images from {workspace_path}")
        
        with open(workspace_path) as f:
            data = json.load(f)
        
        items = data.get('items', {})
        self.logger.info(f"Total images in workspace: {len(items)}")
        
        # Build sample list with metadata
        sample = []
        for path, item_data in items.items():
            if not Path(path).exists():
                continue
            
            # Get previous result if any
            previous_result = None
            if item_data.get('descriptions'):
                desc = item_data['descriptions'][0]
                previous_result = {
                    'had_description': bool(desc.get('text', '').strip()),
                    'model': desc.get('model'),
                    'finish_reason': desc.get('finish_reason'),
                    'completion_tokens': desc.get('completion_tokens')
                }
            
            sample.append({
                'path': path,
                'extension': Path(path).suffix.lower(),
                'previous_result': previous_result
            })
        
        # Filter to existing files
        sample = [s for s in sample if Path(s['path']).exists()]
        self.logger.info(f"Accessible images: {len(sample)}")
        
        # Apply selection strategy
        if strategy == 'random':
            selected = random.sample(sample, min(count, len(sample)))
        elif strategy == 'failed_first':
            # Prioritize previously failed images
            failed = [s for s in sample if s['previous_result'] and not s['previous_result']['had_description']]
            success = [s for s in sample if s['previous_result'] and s['previous_result']['had_description']]
            no_result = [s for s in sample if not s['previous_result']]
            selected = (failed[:count//2] + success[:count//4] + no_result[:count//4])[:count]
        elif strategy == 'png_heavy':
            # Include more PNGs (59% failure rate)
            png = [s for s in sample if s['extension'] == '.png']
            other = [s for s in sample if s['extension'] != '.png']
            selected = png + random.sample(other, min(count - len(png), len(other)))
            selected = selected[:count]
        else:
            selected = sample[:count]
        
        self.logger.info(f"Selected {len(selected)} images ({strategy} strategy)")
        
        # Log file type distribution
        extensions = Counter(s['extension'] for s in selected)
        self.logger.info(f"File types: {dict(extensions)}")
        
        return selected
    
    def convert_png_to_jpeg(self, image_path: str) -> Optional[str]:
        """Convert PNG to JPEG, return base64 or None"""
        if not HAS_PIL:
            return None
        
        try:
            img = Image.open(image_path)
            
            # Convert to RGB
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize if needed
            max_dim = 1600
            if max(img.size) > max_dim:
                img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
            
            # Save as JPEG
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=85, optimize=True)
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        except Exception as e:
            self.logger.warning(f"PNG conversion failed for {image_path}: {e}")
            return None
    
    def test_image(self, image_path: str, model: str, prompt: str,
                   max_tokens: int = 1000, convert_png: bool = False) -> Dict[str, Any]:
        """Test single image with specified parameters"""
        
        start_time = time.time()
        
        # Load image
        file_ext = Path(image_path).suffix.lower()
        image_data = None
        
        if convert_png and file_ext == '.png':
            image_data = self.convert_png_to_jpeg(image_path)
            if image_data:
                self.logger.debug(f"Converted PNG to JPEG: {image_path}")
        
        if image_data is None:
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
        
        # Build request
        request_params = {
            "model": model,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                ]
            }]
        }
        
        # Set max_tokens (GPT-5+ uses different param name)
        if model.startswith('gpt-5') or model.startswith('o1') or model.startswith('o3'):
            request_params["max_completion_tokens"] = max_tokens
        else:
            request_params["max_tokens"] = max_tokens
        
        try:
            # Make API call
            response = self.client.chat.completions.create(**request_params)
            
            # Extract response data
            content = response.choices[0].message.content or ""
            finish_reason = response.choices[0].finish_reason
            
            result = {
                "status": "empty" if not content.strip() else "success",
                "image_path": image_path,
                "image_extension": file_ext,
                "model": model,
                "parameters": {
                    "max_tokens": max_tokens,
                    "png_converted": convert_png and file_ext == '.png' and image_data
                },
                "response": {
                    "text": content,
                    "text_length": len(content),
                    "finish_reason": finish_reason,
                    "completion_tokens": response.usage.completion_tokens,
                    "prompt_tokens": response.usage.prompt_tokens,
                    "total_tokens": response.usage.total_tokens,
                    "response_id": response.id,
                    "model_returned": response.model
                },
                "processing_time": time.time() - start_time
            }
            
            # Log empty responses
            if result["status"] == "empty":
                self.logger.warning(
                    f"EMPTY: {model} | {Path(image_path).name} | "
                    f"finish={finish_reason} | tokens={response.usage.completion_tokens}"
                )
            else:
                self.logger.info(
                    f"SUCCESS: {model} | {Path(image_path).name} | "
                    f"chars={len(content)} | tokens={response.usage.completion_tokens}"
                )
            
            return result
        
        except Exception as e:
            self.logger.error(f"ERROR: {model} | {image_path} | {e}")
            return {
                "status": "error",
                "image_path": image_path,
                "image_extension": file_ext,
                "model": model,
                "error": str(e),
                "processing_time": time.time() - start_time
            }
    
    def run_phase_1(self, sample_images: List[Dict]) -> List[Dict]:
        """Phase 1: Model validation (3 images × 4 models)"""
        
        self.logger.info("=" * 80)
        self.logger.info("PHASE 1: Model Validation")
        self.logger.info("Testing 3 images × 4 OpenAI models = 12 requests")
        self.logger.info("=" * 80)
        
        # Select 3 test images (1 failed, 1 success, 1 PNG)
        test_images = sample_images[:3]
        
        models = ['gpt-5-nano-2025-08-07', 'gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo']
        prompt = "Describe this image in 2-3 sentences."
        
        results = []
        for img in test_images:
            for model in models:
                self.logger.info(f"Testing {model} with {Path(img['path']).name}")
                result = self.test_image(img['path'], model, prompt, max_tokens=1000)
                results.append(result)
                time.sleep(1)  # Rate limiting
        
        self.save_results(results, "phase1_model_validation")
        self.print_summary(results, "Phase 1: Model Validation")
        
        return results
    
    def run_phase_2(self, sample_images: List[Dict]) -> List[Dict]:
        """Phase 2: gpt-5-nano baseline (100 images, original params)"""
        
        self.logger.info("=" * 80)
        self.logger.info("PHASE 2: gpt-5-nano Baseline Test")
        self.logger.info("Testing 100 images with original parameters")
        self.logger.info("=" * 80)
        
        model = 'gpt-5-nano-2025-08-07'
        prompt = "Describe this image in narrative form."
        
        results = []
        for i, img in enumerate(sample_images[:100], 1):
            self.logger.info(f"[{i}/100] Testing {Path(img['path']).name}")
            result = self.test_image(
                img['path'], model, prompt,
                max_tokens=1000,
                convert_png=False
            )
            results.append(result)
            time.sleep(1)
        
        self.save_results(results, "phase2_nano_baseline")
        self.print_summary(results, "Phase 2: Baseline (max_tokens=1000, no PNG conversion)")
        
        return results
    
    def run_phase_3(self, sample_images: List[Dict]) -> List[Dict]:
        """Phase 3: gpt-5-nano optimized (100 images, ChatGPT recommendations)"""
        
        self.logger.info("=" * 80)
        self.logger.info("PHASE 3: gpt-5-nano Optimized Test")
        self.logger.info("Testing 100 images with ChatGPT recommendations")
        self.logger.info("max_tokens=300, PNG→JPEG conversion enabled")
        self.logger.info("=" * 80)
        
        model = 'gpt-5-nano-2025-08-07'
        prompt = "Describe this image in narrative form."
        
        results = []
        for i, img in enumerate(sample_images[:100], 1):
            self.logger.info(f"[{i}/100] Testing {Path(img['path']).name}")
            result = self.test_image(
                img['path'], model, prompt,
                max_tokens=300,
                convert_png=True
            )
            results.append(result)
            time.sleep(1)
        
        self.save_results(results, "phase3_nano_optimized")
        self.print_summary(results, "Phase 3: Optimized (max_tokens=300, PNG conversion ON)")
        
        return results
    
    def save_results(self, results: List[Dict], phase_name: str):
        """Save results to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{phase_name}_{timestamp}.json"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)
        
        self.logger.info(f"Results saved to: {filepath}")
    
    def print_summary(self, results: List[Dict], phase_title: str):
        """Print summary statistics"""
        
        total = len(results)
        success = sum(1 for r in results if r['status'] == 'success')
        empty = sum(1 for r in results if r['status'] == 'empty')
        errors = sum(1 for r in results if r['status'] == 'error')
        
        self.logger.info("")
        self.logger.info("=" * 80)
        self.logger.info(f"SUMMARY: {phase_title}")
        self.logger.info("=" * 80)
        self.logger.info(f"Total requests:     {total}")
        self.logger.info(f"Success:            {success} ({success/total*100:.1f}%)")
        self.logger.info(f"Empty responses:    {empty} ({empty/total*100:.1f}%)")
        self.logger.info(f"Errors:             {errors} ({errors/total*100:.1f}%)")
        
        # finish_reason distribution for empty responses
        if empty > 0:
            empty_results = [r for r in results if r['status'] == 'empty']
            finish_reasons = Counter(r['response']['finish_reason'] for r in empty_results if 'response' in r)
            self.logger.info("")
            self.logger.info("Empty response finish_reason distribution:")
            for reason, count in finish_reasons.most_common():
                self.logger.info(f"  {reason}: {count}")
            
            # Check completion_tokens
            avg_tokens = sum(r['response']['completion_tokens'] for r in empty_results if 'response' in r) / len(empty_results)
            self.logger.info(f"  Avg completion_tokens: {avg_tokens:.1f}")
        
        # File type breakdown
        by_ext = {}
        for r in results:
            ext = r['image_extension']
            if ext not in by_ext:
                by_ext[ext] = {'total': 0, 'empty': 0}
            by_ext[ext]['total'] += 1
            if r['status'] == 'empty':
                by_ext[ext]['empty'] += 1
        
        self.logger.info("")
        self.logger.info("Failure rate by file type:")
        for ext, stats in sorted(by_ext.items()):
            rate = stats['empty'] / stats['total'] * 100 if stats['total'] > 0 else 0
            self.logger.info(f"  {ext}: {stats['empty']}/{stats['total']} ({rate:.1f}%)")
        
        self.logger.info("=" * 80)
        self.logger.info("")


def load_api_key_from_config() -> Optional[str]:
    """Load API key from image_describer_config.json"""
    try:
        config_path = Path('scripts/image_describer_config.json')
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
            api_keys = config.get('api_keys', {})
            for key in ['OpenAI', 'openai', 'OPENAI']:
                if key in api_keys and api_keys[key]:
                    return api_keys[key].strip()
    except Exception as e:
        print(f"Warning: Error loading config file: {e}")
    return None


def main():
    parser = argparse.ArgumentParser(description='Test OpenAI models systematically')
    parser.add_argument('--phase', type=int, choices=[1, 2, 3], help='Run specific phase')
    parser.add_argument('--all', action='store_true', help='Run all phases')
    parser.add_argument('--workspace', type=str, 
                       default='/Users/kellyford/Documents/ImageDescriptionToolkit/workspaces/EuropeNano509_20260214.idw',
                       help='Path to workspace file')
    parser.add_argument('--api-key', type=str,
                       help='OpenAI API key (or use config file or OPENAI_API_KEY env var)')
    parser.add_argument('--output-dir', type=str,
                       default='test_results',
                       help='Directory for test results')
    
    args = parser.parse_args()
    
    # Load API key from multiple sources (same as main app)
    api_key = args.api_key or os.getenv('OPENAI_API_KEY') or load_api_key_from_config()
    
    if not api_key:
        print("ERROR: No API key found")
        print("Provide via --api-key, OPENAI_API_KEY env var, or scripts/image_describer_config.json")
        exit(1)
    
    # Initialize tester
    output_dir = Path(args.output_dir)
    tester = OpenAITester(api_key, output_dir)
    
    # Load image sample
    workspace_path = Path(args.workspace)
    if not workspace_path.exists():
        print(f"ERROR: Workspace file not found: {workspace_path}")
        exit(1)
    
    sample_images = tester.load_image_sample(workspace_path, count=100, strategy='random')
    
    # Run requested phases
    if args.phase == 1 or args.all:
        tester.run_phase_1(sample_images)
    
    if args.phase == 2 or args.all:
        tester.run_phase_2(sample_images)
    
    if args.phase == 3 or args.all:
        tester.run_phase_3(sample_images)
    
    if not args.phase and not args.all:
        parser.print_help()


if __name__ == '__main__':
    main()
