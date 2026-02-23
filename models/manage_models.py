#!/usr/bin/env python3
"""
Model Manager - Image Description Toolkit

Manage AI models across all providers - install, remove, list, and get info.
This is a standalone tool that works independently of the GUI and scripts.

Supported Providers:
    - Ollama (local vision models)
    - OpenAI (cloud API models)
    - Claude (Anthropic cloud API models)

Usage:
    python -m models.manage_models list                           # List all available models
    python -m models.manage_models list --installed               # List only installed models
    python -m models.manage_models list --provider ollama         # List models for specific provider
    python -m models.manage_models install llava:7b               # Install an Ollama model
    python -m models.manage_models remove llava:7b                # Remove an Ollama model
    python -m models.manage_models info llava:7b                  # Get model information
    python -m models.manage_models recommend                      # Get model recommendations
    python -m models.manage_models install --recommended          # Install recommended Ollama models
"""

import sys
import json
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import Claude model list from central source so this file never needs
# to be edited when models are added or deprecated - only claude_models.py does.
try:
    from models.claude_models import CLAUDE_MODELS as _CLAUDE_MODEL_IDS, CLAUDE_MODEL_METADATA as _CLAUDE_MODEL_META
except ImportError:
    from claude_models import CLAUDE_MODELS as _CLAUDE_MODEL_IDS, CLAUDE_MODEL_METADATA as _CLAUDE_MODEL_META

try:
    from colorama import Fore, Style, init
    init(autoreset=True)
    COLORS_AVAILABLE = True
except ImportError:
    COLORS_AVAILABLE = False
    class Fore:
        GREEN = RED = YELLOW = BLUE = CYAN = MAGENTA = ""
    class Style:
        BRIGHT = RESET_ALL = ""


# Model metadata database
MODEL_METADATA = {
    # Ollama Models
    "llava:7b": {
        "provider": "ollama",
        "description": "LLaVA 7B - Good balance of speed and quality",
        "size": "4.7GB",
        "install_command": "ollama pull llava:7b",
        "recommended": True,
        "min_ram": "8GB",
        "tags": ["vision", "multimodal", "recommended"]
    },
    "llava:latest": {
        "provider": "ollama",
        "description": "LLaVA - Latest version",
        "size": "~4.7GB",
        "install_command": "ollama pull llava",
        "recommended": True,
        "min_ram": "8GB",
        "tags": ["vision", "multimodal"]
    },
    "moondream:latest": {
        "provider": "ollama",
        "description": "Moondream - Fastest, smallest vision model",
        "size": "1.7GB",
        "install_command": "ollama pull moondream",
        "recommended": True,
        "min_ram": "4GB",
        "tags": ["vision", "fast", "lightweight", "recommended"]
    },
    "llama3.2-vision:11b": {
        "provider": "ollama",
        "description": "Llama 3.2 Vision 11B - Most accurate",
        "size": "7.5GB",
        "install_command": "ollama pull llama3.2-vision:11b",
        "recommended": True,
        "min_ram": "12GB",
        "tags": ["vision", "accurate", "recommended"]
    },
    "llama3.2-vision:latest": {
        "provider": "ollama",
        "description": "Llama 3.2 Vision - Latest version",
        "size": "~7.5GB",
        "install_command": "ollama pull llama3.2-vision",
        "recommended": True,
        "min_ram": "12GB",
        "tags": ["vision", "accurate"]
    },
    "bakllava:latest": {
        "provider": "ollama",
        "description": "BakLLaVA - Vision model variant",
        "size": "~4.7GB",
        "install_command": "ollama pull bakllava",
        "recommended": False,
        "min_ram": "8GB",
        "tags": ["vision", "multimodal"]
    },
    "llava-llama3:latest": {
        "provider": "ollama",
        "description": "LLaVA with Llama 3 base",
        "size": "~5.5GB",
        "install_command": "ollama pull llava-llama3",
        "recommended": False,
        "min_ram": "8GB",
        "tags": ["vision", "multimodal"]
    },
    "gemma3:latest": {
        "provider": "ollama",
        "description": "Gemma 3 - Google's vision model",
        "size": "~5GB",
        "install_command": "ollama pull gemma3",
        "recommended": False,
        "min_ram": "8GB",
        "tags": ["vision"]
    },
    "mistral-small3.1:latest": {
        "provider": "ollama",
        "description": "Mistral Small 3.1",
        "size": "~4GB",
        "install_command": "ollama pull mistral-small3.1",
        "recommended": False,
        "min_ram": "8GB",
        "tags": ["text"]
    },
    
    # OpenAI Models — verified 2026-02-23 via live API test
    # See models/openai_models.py for full canonical list
    "gpt-5.2": {
        "provider": "openai",
        "description": "GPT-5.2 - Best model for coding and agentic tasks",
        "size": "Cloud-based",
        "install_command": "Requires API key in openai.txt",
        "recommended": True,
        "cost": "$$$$",
        "tags": ["vision", "cloud", "accurate", "recommended"]
    },
    "gpt-5.1": {
        "provider": "openai",
        "description": "GPT-5.1 - Mid-tier GPT-5 reasoning model",
        "size": "Cloud-based",
        "install_command": "Requires API key in openai.txt",
        "recommended": False,
        "cost": "$$$",
        "tags": ["vision", "cloud", "accurate"]
    },
    "gpt-5": {
        "provider": "openai",
        "description": "GPT-5 - Previous flagship reasoning model",
        "size": "Cloud-based",
        "install_command": "Requires API key in openai.txt",
        "recommended": False,
        "cost": "$$$",
        "tags": ["vision", "cloud", "accurate"]
    },
    "gpt-5-mini": {
        "provider": "openai",
        "description": "GPT-5 Mini - Faster, cost-efficient GPT-5",
        "size": "Cloud-based",
        "install_command": "Requires API key in openai.txt",
        "recommended": False,
        "cost": "$$",
        "tags": ["vision", "cloud", "fast"]
    },
    "gpt-5-nano": {
        "provider": "openai",
        "description": "GPT-5 Nano - Fastest, most affordable GPT-5",
        "size": "Cloud-based",
        "install_command": "Requires API key in openai.txt",
        "recommended": False,
        "cost": "$",
        "tags": ["vision", "cloud", "fast"]
    },
    "o4-mini": {
        "provider": "openai",
        "description": "o4-mini - Fast cost-efficient reasoning model",
        "size": "Cloud-based",
        "install_command": "Requires API key in openai.txt",
        "recommended": False,
        "cost": "$$",
        "tags": ["vision", "cloud", "reasoning"]
    },
    "o3": {
        "provider": "openai",
        "description": "o3 - Reasoning model for complex tasks",
        "size": "Cloud-based",
        "install_command": "Requires API key in openai.txt",
        "recommended": False,
        "cost": "$$$",
        "tags": ["vision", "cloud", "reasoning"]
    },
    "o1": {
        "provider": "openai",
        "description": "o1 - Previous o-series reasoning model (slow)",
        "size": "Cloud-based",
        "install_command": "Requires API key in openai.txt",
        "recommended": False,
        "cost": "$$$",
        "tags": ["vision", "cloud", "reasoning"]
    },
    "gpt-4o": {
        "provider": "openai",
        "description": "GPT-4o - Fast, intelligent, flexible multimodal model",
        "size": "Cloud-based",
        "install_command": "Requires API key in openai.txt",
        "recommended": True,
        "cost": "$$",
        "tags": ["vision", "cloud", "accurate", "recommended"]
    },
    "gpt-4o-mini": {
        "provider": "openai",
        "description": "GPT-4o Mini - Fast and affordable",
        "size": "Cloud-based",
        "install_command": "Requires API key in openai.txt",
        "recommended": True,
        "cost": "$",
        "tags": ["vision", "cloud", "fast", "recommended"]
    },
    "gpt-4.1": {
        "provider": "openai",
        "description": "GPT-4.1 - Smartest non-reasoning model",
        "size": "Cloud-based",
        "install_command": "Requires API key in openai.txt",
        "recommended": False,
        "cost": "$$",
        "tags": ["vision", "cloud", "accurate"]
    },
    "gpt-4.1-mini": {
        "provider": "openai",
        "description": "GPT-4.1 Mini - Smaller GPT-4.1",
        "size": "Cloud-based",
        "install_command": "Requires API key in openai.txt",
        "recommended": False,
        "cost": "$",
        "tags": ["vision", "cloud", "fast"]
    },
    "gpt-4.1-nano": {
        "provider": "openai",
        "description": "GPT-4.1 Nano - Ultra-budget GPT-4.1",
        "size": "Cloud-based",
        "install_command": "Requires API key in openai.txt",
        "recommended": False,
        "cost": "$",
        "tags": ["vision", "cloud", "fast"]
    },
    
    # Claude (Anthropic) Models - populated dynamically below from models.claude_models
    # To add/remove Claude models, edit models/claude_models.py only.

    # HuggingFace Models (Florence-2)
    "microsoft/Florence-2-base": {
        "provider": "huggingface",
        "description": "Florence-2 Base - Fast local vision model with NPU support",
        "size": "~230MB",
        "install_command": "pip install 'transformers>=4.45.0' torch torchvision pillow",
        "recommended": True,
        "min_ram": "4GB",
        "cost": "Free",
        "tags": ["vision", "local", "npu", "fast", "recommended"]
    },
    "microsoft/Florence-2-large": {
        "provider": "huggingface",
        "description": "Florence-2 Large - Higher quality local vision model with NPU support",
        "size": "~700MB",
        "install_command": "pip install 'transformers>=4.45.0' torch torchvision pillow",
        "recommended": True,
        "min_ram": "8GB",
        "cost": "Free",
        "tags": ["vision", "local", "npu", "accurate", "recommended"]
    },
}


# Populate Claude entries from the central model registry.
# This runs once at import time so MODEL_METADATA is fully populated before use.
for _model_id in _CLAUDE_MODEL_IDS:
    _meta = _CLAUDE_MODEL_META.get(_model_id, {})
    _recommended = _meta.get("recommended", False)
    MODEL_METADATA[_model_id] = {
        "provider": "claude",
        "description": _meta.get("description", "Claude model"),
        "size": "Cloud-based",
        "install_command": "Requires API key in claude.txt or ANTHROPIC_API_KEY",
        "recommended": _recommended,
        "cost": _meta.get("cost", "$$"),
        "tags": ["vision", "cloud"] + (["recommended"] if _recommended else []),
    }


def get_installed_ollama_models() -> List[str]:
    """Get list of installed Ollama models."""
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return [m['name'] for m in data.get('models', [])]
    except:
        pass
    return []


def is_ollama_running() -> bool:
    """Check if Ollama service is running."""
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        return response.status_code == 200
    except:
        return False


def install_ollama_model(model_name: str) -> bool:
    """Install an Ollama model."""
    if not is_ollama_running():
        print(f"{Fore.RED}Error: Ollama service is not running{Style.RESET_ALL}")
        print(f"Start Ollama first, then try again")
        return False
    
    print(f"Installing {model_name}...")
    print(f"{Fore.YELLOW}This may take several minutes depending on model size{Style.RESET_ALL}")
    
    try:
        result = subprocess.run(
            ['ollama', 'pull', model_name],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"{Fore.GREEN}[OK] Successfully installed {model_name}{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}[FAIL] Failed to install {model_name}{Style.RESET_ALL}")
            print(result.stderr)
            return False
    except FileNotFoundError:
        print(f"{Fore.RED}Error: 'ollama' command not found{Style.RESET_ALL}")
        print(f"Install Ollama from: https://ollama.ai")
        return False


def remove_ollama_model(model_name: str) -> bool:
    """Remove an Ollama model."""
    if not is_ollama_running():
        print(f"{Fore.RED}Error: Ollama service is not running{Style.RESET_ALL}")
        return False
    
    print(f"Removing {model_name}...")
    
    try:
        result = subprocess.run(
            ['ollama', 'rm', model_name],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"{Fore.GREEN}[OK] Successfully removed {model_name}{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}[FAIL] Failed to remove {model_name}{Style.RESET_ALL}")
            print(result.stderr)
            return False
    except FileNotFoundError:
        print(f"{Fore.RED}Error: 'ollama' command not found{Style.RESET_ALL}")
        return False





def get_all_installed_models() -> Dict[str, List[str]]:
    """Get all installed models grouped by provider."""
    installed = {
        "ollama": get_installed_ollama_models()
    }
    
    return installed


def remove_ollama_model(model_name: str) -> bool:
    """Remove an Ollama model."""
    if not is_ollama_running():
        print(f"{Fore.RED}Error: Ollama service is not running{Style.RESET_ALL}")
        return False
    
    print(f"Removing {model_name}...")
    
    try:
        result = subprocess.run(
            ['ollama', 'rm', model_name],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"{Fore.GREEN}[OK] Successfully removed {model_name}{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.RED}[FAIL] Failed to remove {model_name}{Style.RESET_ALL}")
            print(result.stderr)
            return False
    except FileNotFoundError:
        print(f"{Fore.RED}Error: 'ollama' command not found{Style.RESET_ALL}")
        return False


def list_models(installed_only: bool = False, provider: Optional[str] = None):
    """List all available models."""
    all_installed = get_all_installed_models()
    
    print(f"{Style.BRIGHT}=== Available Models ==={Style.RESET_ALL}\n")
    
    # Group by provider
    providers = {}
    for model_name, metadata in MODEL_METADATA.items():
        prov = metadata['provider']
        if provider and prov != provider:
            continue
        if prov not in providers:
            providers[prov] = []
        providers[prov].append((model_name, metadata))
    
    for prov_name in sorted(providers.keys()):
        models = providers[prov_name]
        
        print(f"{Style.BRIGHT}{prov_name.upper()}{Style.RESET_ALL}")
        
        for model_name, metadata in sorted(models, key=lambda x: x[1].get('recommended', False), reverse=True):
            # Check if installed
            is_installed = False
            if prov_name in all_installed:
                is_installed = model_name in all_installed[prov_name]
            
            if installed_only and not is_installed:
                continue
            
            # Format model line
            if is_installed:
                status = f"{Fore.GREEN}[INSTALLED]{Style.RESET_ALL}"
            else:
                status = f"{Fore.YELLOW}[AVAILABLE]{Style.RESET_ALL}"
            
            recommended = f" {Fore.CYAN}[RECOMMENDED]{Style.RESET_ALL}" if metadata.get('recommended') else ""
            
            print(f"  {status} {Style.BRIGHT}{model_name}{Style.RESET_ALL}{recommended}")
            print(f"    {metadata['description']}")
            print(f"    Size: {metadata['size']}", end="")
            
            if metadata.get('min_ram'):
                print(f" | Min RAM: {metadata['min_ram']}", end="")
            if metadata.get('cost'):
                print(f" | Cost: {metadata['cost']}", end="")
            
            print()
            
            if not is_installed:
                print(f"    {Fore.CYAN}Install: {metadata['install_command']}{Style.RESET_ALL}")
            
            print()
        
        print()


def show_model_info(model_name: str):
    """Show detailed information about a specific model."""
    if model_name not in MODEL_METADATA:
        print(f"{Fore.RED}Model '{model_name}' not found in database{Style.RESET_ALL}")
        print(f"\nUse 'python -m models.manage_models list' to see available models")
        return
    
    metadata = MODEL_METADATA[model_name]
    all_installed = get_all_installed_models()
    
    # Check if installed
    is_installed = False
    provider = metadata['provider']
    if provider in all_installed:
        is_installed = model_name in all_installed[provider]
    
    print(f"{Style.BRIGHT}=== Model Information ==={Style.RESET_ALL}\n")
    print(f"Name: {Style.BRIGHT}{model_name}{Style.RESET_ALL}")
    print(f"Provider: {metadata['provider']}")
    print(f"Description: {metadata['description']}")
    print(f"Size: {metadata['size']}")
    
    if metadata.get('min_ram'):
        print(f"Minimum RAM: {metadata['min_ram']}")
    if metadata.get('cost'):
        print(f"Cost: {metadata['cost']}")
    
    print(f"Tags: {', '.join(metadata.get('tags', []))}")
    print(f"Recommended: {'Yes' if metadata.get('recommended') else 'No'}")
    
    if is_installed:
        print(f"\nStatus: {Fore.GREEN}[INSTALLED]{Style.RESET_ALL}")
    else:
        print(f"\nStatus: {Fore.YELLOW}[NOT INSTALLED]{Style.RESET_ALL}")
        print(f"\nInstallation: {metadata['install_command']}")


def show_recommendations():
    """Show model recommendations based on use case."""
    print(f"{Style.BRIGHT}=== Model Recommendations ==={Style.RESET_ALL}\n")
    
    print(f"{Style.BRIGHT}Quick Start - Local Models (Choose One):{Style.RESET_ALL}")
    print(f"  • {Fore.CYAN}moondream:latest{Style.RESET_ALL} - Fastest, smallest (1.7GB)")
    print(f"    Best for: Quick testing, limited RAM, batch processing")
    print(f"    Install: ollama pull moondream\n")
    
    print(f"  • {Fore.CYAN}llava:7b{Style.RESET_ALL} - Balanced quality & speed (4.7GB)")
    print(f"    Best for: General use, good results, moderate speed")
    print(f"    Install: ollama pull llava:7b\n")
    
    print(f"  • {Fore.CYAN}llama3.2-vision:11b{Style.RESET_ALL} - Most accurate (7.5GB)")
    print(f"    Best for: Maximum quality, detailed descriptions")
    print(f"    Install: ollama pull llama3.2-vision:11b\n")
    
    print(f"{Style.BRIGHT}Cloud Options:{Style.RESET_ALL}")
    print(f"  • {Fore.CYAN}gpt-4o-mini{Style.RESET_ALL} - Fast & affordable cloud")
    print(f"    Best for: No local GPU, quick results, API access")
    print(f"    Setup: Add OpenAI API key to openai.txt\n")
    
    print(f"  • {Fore.CYAN}gpt-4o{Style.RESET_ALL} - Best quality cloud")
    print(f"    Best for: Maximum accuracy, complex images")
    print(f"    Setup: Add OpenAI API key to openai.txt\n")
    
    print(f"  • {Fore.CYAN}claude-sonnet-4-5-20250929{Style.RESET_ALL} - High quality cloud")
    print(f"    Best for: Detailed analysis, complex reasoning")
    print(f"    Setup: Add Anthropic API key to claude.txt\n")
    
    # Check current installation status
    all_installed = get_all_installed_models()
    
    print(f"{Style.BRIGHT}Your Installed Components:{Style.RESET_ALL}")
    has_anything = False
    
    if all_installed["ollama"]:
        print(f"  {Fore.GREEN}[Ollama Models]{Style.RESET_ALL}")
        for model in all_installed["ollama"]:
            print(f"    ✓ {model}")
        has_anything = True
    
    if not has_anything:
        print(f"  {Fore.YELLOW}No models installed yet{Style.RESET_ALL}")
        print(f"  Install a recommended model to get started!")


def install_recommended_models():
    """Install all recommended models."""
    if not is_ollama_running():
        print(f"{Fore.RED}Error: Ollama service is not running{Style.RESET_ALL}")
        print(f"Start Ollama first, then try again")
        return
    
    recommended = [
        name for name, meta in MODEL_METADATA.items()
        if meta.get('recommended') and meta['provider'] == 'ollama'
    ]
    
    print(f"{Style.BRIGHT}Installing {len(recommended)} recommended models{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}This will download approximately 20GB of data{Style.RESET_ALL}")
    
    response = input(f"\nContinue? (y/N): ")
    if response.lower() != 'y':
        print("Cancelled")
        return
    
    for model_name in recommended:
        print(f"\n{Style.BRIGHT}Installing {model_name}...{Style.RESET_ALL}")
        install_ollama_model(model_name)


def main():
    parser = argparse.ArgumentParser(
        description='Manage AI models for Image Description Toolkit',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m models.manage_models list                      # List all models
  python -m models.manage_models list --installed          # List installed models only
  python -m models.manage_models list --provider ollama    # List Ollama models
  python -m models.manage_models install llava:7b          # Install Ollama model
  python -m models.manage_models remove llava:7b           # Remove Ollama model
  python -m models.manage_models info llava:7b             # Get model info
  python -m models.manage_models recommend                 # Show recommendations
  python -m models.manage_models install --recommended     # Install all recommended Ollama models
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List available models')
    list_parser.add_argument('--installed', action='store_true', help='Show only installed models')
    list_parser.add_argument('--provider', choices=['ollama', 'openai', 'claude', 'huggingface'], help='Filter by provider')
    
    # Install command
    install_parser = subparsers.add_parser('install', help='Install a model')
    install_parser.add_argument('model', nargs='?', help='Model name to install')
    install_parser.add_argument('--recommended', action='store_true', help='Install all recommended models')
    
    # Remove command
    remove_parser = subparsers.add_parser('remove', help='Remove a model')
    remove_parser.add_argument('model', help='Model name to remove')
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Show model information')
    info_parser.add_argument('model', help='Model name')
    
    # Recommend command
    recommend_parser = subparsers.add_parser('recommend', help='Show model recommendations')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == 'list':
        list_models(installed_only=args.installed, provider=args.provider)
    
    elif args.command == 'install':
        if args.recommended:
            install_recommended_models()
        elif args.model:
            # Determine provider and install accordingly
            if args.model in MODEL_METADATA:
                metadata = MODEL_METADATA[args.model]
                provider = metadata['provider']
                
                if provider == 'ollama':
                    install_ollama_model(args.model)
                elif provider == 'openai':
                    print(f"OpenAI models require an API key.")
                    print(f"Add your API key to 'openai.txt' or set OPENAI_API_KEY environment variable")
                elif provider == 'claude':
                    print(f"Claude models require an API key.")
                    print(f"Add your API key to 'claude.txt' or set ANTHROPIC_API_KEY environment variable")
                else:
                    print(f"Installation for {provider} not supported via this tool")
            else:
                # Try as Ollama model directly
                install_ollama_model(args.model)
        else:
            print("Error: Specify a model name or use --recommended")
            install_parser.print_help()
    
    elif args.command == 'remove':
        remove_ollama_model(args.model)
    
    elif args.command == 'info':
        show_model_info(args.model)
    
    elif args.command == 'recommend':
        show_recommendations()


if __name__ == "__main__":
    main()
