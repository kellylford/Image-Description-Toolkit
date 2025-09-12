#!/usr/bin/env python3
"""
Hugging Face Model Pre-downloader
Similar to 'ollama pull', this script downloads HF models ahead of time.

Usage:
    python download_hf_models.py --all                    # Download all supported models
    python download_hf_models.py --model blip2-opt        # Download specific model
    python download_hf_models.py --list                   # List available models
"""

import argparse
import sys
from pathlib import Path

# Add the imagedescriber module to path
sys.path.append('imagedescriber')

try:
    from transformers import AutoProcessor, AutoModelForVision2Seq, BlipProcessor, BlipForConditionalGeneration
    from transformers import InstructBlipProcessor, InstructBlipForConditionalGeneration
    from transformers import LlavaNextProcessor, LlavaNextForConditionalGeneration
    from transformers import GitProcessor, GitForCausalLM
    import torch
except ImportError as e:
    print(f"Error: Required packages not installed. Please run: pip install transformers torch accelerate")
    print(f"Details: {e}")
    sys.exit(1)

# Supported models (same as in the app)
SUPPORTED_MODELS = {
    'blip2-opt': {
        'repo': 'Salesforce/blip2-opt-2.7b',
        'processor_class': AutoProcessor,
        'model_class': AutoModelForVision2Seq,
        'description': 'BLIP-2 with OPT-2.7B language model'
    },
    'blip2-flan': {
        'repo': 'Salesforce/blip2-flan-t5-xl', 
        'processor_class': AutoProcessor,
        'model_class': AutoModelForVision2Seq,
        'description': 'BLIP-2 with Flan-T5-XL language model'
    },
    'instructblip': {
        'repo': 'Salesforce/instructblip-vicuna-7b',
        'processor_class': InstructBlipProcessor,
        'model_class': InstructBlipForConditionalGeneration,
        'description': 'InstructBLIP with Vicuna-7B'
    },
    'llava': {
        'repo': 'llava-hf/llava-1.5-7b-hf',
        'processor_class': LlavaNextProcessor,
        'model_class': LlavaNextForConditionalGeneration,
        'description': 'LLaVA 1.5 7B model'
    },
    'git-base': {
        'repo': 'microsoft/git-base-coco',
        'processor_class': GitProcessor,
        'model_class': GitForCausalLM,
        'description': 'GIT model trained on COCO'
    },
    'minicpm': {
        'repo': 'openbmb/MiniCPM-V-2',
        'processor_class': AutoProcessor,
        'model_class': AutoModelForVision2Seq,
        'description': 'MiniCPM-V-2 vision-language model'
    }
}

def list_models():
    """List all available models"""
    print("Available Hugging Face models:")
    print("-" * 50)
    for key, info in SUPPORTED_MODELS.items():
        print(f"{key:15} - {info['description']}")
        print(f"{'':15}   Repository: {info['repo']}")
        print()

def download_model(model_key: str):
    """Download a specific model"""
    if model_key not in SUPPORTED_MODELS:
        print(f"Error: Model '{model_key}' not found.")
        print("Use --list to see available models.")
        return False
        
    model_info = SUPPORTED_MODELS[model_key]
    repo = model_info['repo']
    
    print(f"Downloading {model_key} ({repo})...")
    print(f"Description: {model_info['description']}")
    print("-" * 60)
    
    try:
        # Download processor
        print("📥 Downloading processor...")
        processor = model_info['processor_class'].from_pretrained(
            repo,
            trust_remote_code=True
        )
        print("✅ Processor downloaded successfully")
        
        # Download model
        print("📥 Downloading model (this may take several minutes)...")
        model = model_info['model_class'].from_pretrained(
            repo,
            trust_remote_code=True,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto" if torch.cuda.is_available() else None
        )
        print("✅ Model downloaded successfully")
        
        # Clear memory
        del model
        del processor
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            
        print(f"🎉 Successfully downloaded {model_key}!")
        return True
        
    except Exception as e:
        print(f"❌ Error downloading {model_key}: {e}")
        return False

def download_all_models():
    """Download all supported models"""
    print(f"Downloading all {len(SUPPORTED_MODELS)} supported models...")
    print("This will take a significant amount of time and disk space.")
    print()
    
    successful = 0
    failed = 0
    
    for i, model_key in enumerate(SUPPORTED_MODELS.keys(), 1):
        print(f"\n[{i}/{len(SUPPORTED_MODELS)}] Processing {model_key}...")
        if download_model(model_key):
            successful += 1
        else:
            failed += 1
            
    print("\n" + "="*60)
    print(f"Download Summary:")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Total: {len(SUPPORTED_MODELS)}")

def main():
    parser = argparse.ArgumentParser(
        description="Download Hugging Face models for Image Description Toolkit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python download_hf_models.py --list
  python download_hf_models.py --model blip2-opt
  python download_hf_models.py --model llava
  python download_hf_models.py --all
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--list', action='store_true', help='List available models')
    group.add_argument('--model', type=str, help='Download specific model')
    group.add_argument('--all', action='store_true', help='Download all models')
    
    args = parser.parse_args()
    
    if args.list:
        list_models()
    elif args.model:
        download_model(args.model)
    elif args.all:
        download_all_models()

if __name__ == "__main__":
    main()