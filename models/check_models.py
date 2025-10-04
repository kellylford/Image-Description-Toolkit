#!/usr/bin/env python3
"""
Model Status Checker - Image Description Toolkit

Check status of all AI models and providers across the toolkit.
This is a standalone diagnostic tool that works independently of the GUI and scripts.

Usage:
    python -m models.check_models                    # Check all providers
    python -m models.check_models --provider ollama  # Check specific provider
    python -m models.check_models --verbose          # Show detailed info
    python -m models.check_models --json             # Output as JSON for scripting
"""

import sys
import json
import argparse
import warnings
from pathlib import Path
from typing import Dict, List, Tuple
from io import StringIO

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=DeprecationWarning)
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress TensorFlow warnings

# Suppress YOLO loading messages during provider imports
import sys
from io import StringIO
_original_stdout = sys.stdout
_original_stderr = sys.stderr

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from colorama import Fore, Style, init
    init(autoreset=True)
    COLORS_AVAILABLE = True
except ImportError:
    COLORS_AVAILABLE = False
    # Fallback for no colorama
    class Fore:
        GREEN = RED = YELLOW = BLUE = CYAN = ""
    class Style:
        BRIGHT = RESET_ALL = ""

# NOTE: We import providers lazily in functions to avoid triggering
# YOLO model initialization at import time (which is expensive)


class SuppressOutput:
    """Context manager to suppress stdout/stderr"""
    def __enter__(self):
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        sys.stdout = StringIO()
        sys.stderr = StringIO()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr
        return False


def check_ollama_status() -> Tuple[bool, List[str], str]:
    """Check Ollama provider status and installed models."""
    with SuppressOutput():
        from imagedescriber.ai_providers import OllamaProvider
    
    try:
        provider = OllamaProvider()
        if not provider.is_available():
            return False, [], "Ollama service not running"
        
        # Get REAL models (not hardcoded)
        import requests
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                models = [m['name'] for m in data.get('models', [])]
                return True, models, "OK"
            else:
                return True, [], "Connected but no models found"
        except Exception as e:
            return False, [], f"API error: {str(e)}"
    except Exception as e:
        return False, [], f"Error: {str(e)}"


def check_ollama_cloud_status() -> Tuple[bool, List[str], str]:
    """Check Ollama Cloud provider status."""
    with SuppressOutput():
        from imagedescriber.ai_providers import OllamaCloudProvider
    
    try:
        provider = OllamaCloudProvider()
        if not provider.is_available():
            return False, [], "Not signed in to Ollama Cloud (no cloud models found)"
        
        # Get available cloud models from the provider
        models = provider.get_available_models()
        if models:
            return True, models, "OK"
        else:
            return False, [], "No cloud models available"
    except Exception as e:
        return False, [], f"Error: {str(e)}"


def check_openai_status() -> Tuple[bool, List[str], str]:
    """Check OpenAI provider status."""
    with SuppressOutput():
        from imagedescriber.ai_providers import OpenAIProvider
    
    try:
        provider = OpenAIProvider()
        if not provider.is_available():
            return False, [], "API key not configured (need openai.txt or OPENAI_API_KEY)"
        
        # Known OpenAI vision models
        models = [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-4-vision-preview"
        ]
        return True, models, "API key configured"
    except Exception as e:
        return False, [], f"Error: {str(e)}"


def check_huggingface_status() -> Tuple[bool, List[str], str]:
    """Check HuggingFace provider status."""
    # Suppress YOLO loading messages that happen during ai_providers import
    with SuppressOutput():
        from imagedescriber.ai_providers import HuggingFaceProvider
    
    try:
        provider = HuggingFaceProvider()
        if not provider.is_available():
            return False, [], "transformers package not installed"
        
        # Get available HF models
        models = provider.get_available_models()
        
        # Check which models are actually cached locally
        try:
            from pathlib import Path
            cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
            cached_models = []
            
            if cache_dir.exists():
                # Check for each model in cache
                for model in models:
                    # Convert model name to cache format (e.g., "Salesforce/blip-image-captioning-base" -> "models--Salesforce--blip-image-captioning-base")
                    cache_name = "models--" + model.replace("/", "--")
                    model_cache = cache_dir / cache_name
                    if model_cache.exists():
                        cached_models.append(f"{model} (cached)")
                    else:
                        cached_models.append(f"{model} (will download on first use)")
                
                return True, cached_models if cached_models else models, "OK"
            else:
                return True, models, "OK (models will download on first use)"
        except:
            return True, models, "OK"
    except Exception as e:
        return False, [], f"Error: {str(e)}"


def check_onnx_status() -> Tuple[bool, List[str], str]:
    """Check ONNX provider status without initializing heavy models."""
    try:
        # Check for ONNX models in expected directory WITHOUT initializing provider
        # (avoids loading YOLO models multiple times)
        models = []
        onnx_dir = Path("imagedescriber/onnx_models")
        if onnx_dir.exists():
            models = [f.stem for f in onnx_dir.glob("*.onnx")]
        
        # Check if YOLO is available
        yolo_available = False
        try:
            import ultralytics
            yolo_available = True
            models.append("Enhanced Ollama + YOLO (uses Ollama models)")
        except ImportError:
            pass
        
        # Check if onnxruntime is available
        try:
            import onnxruntime
            onnx_available = True
        except ImportError:
            onnx_available = False
            if not yolo_available:
                return False, [], "ONNX Runtime not installed (pip install onnxruntime)"
        
        if models:
            return True, models, "OK"
        else:
            return False, [], "No ONNX models found in imagedescriber/onnx_models"
    except Exception as e:
        return False, [], f"Error: {str(e)}"


def check_copilot_status() -> Tuple[bool, List[str], str]:
    """Check Copilot+ PC provider status."""
    with SuppressOutput():
        from imagedescriber.ai_providers import CopilotProvider
    
    try:
        provider = CopilotProvider()
        if not provider.is_available():
            return False, [], "Copilot+ PC NPU not detected (Windows 11 + NPU required)"
        
        models = ["copilot-npu"]
        return True, models, "NPU available"
    except Exception as e:
        return False, [], f"Error: {str(e)}"


def check_groundingdino_status() -> Tuple[bool, List[str], str]:
    """Check GroundingDINO provider status."""
    try:
        # Check if groundingdino package is available
        try:
            import groundingdino
            from groundingdino.util.inference import Model as GroundingDINOModel
            package_available = True
        except ImportError:
            return False, [], "groundingdino package not installed (run models/install_groundingdino.bat)"
        
        # Package is installed - check for cached models
        from pathlib import Path
        cache_dir = Path.home() / ".cache" / "groundingdino"
        
        models = ["GroundingDINO (Text-Prompted Detection)"]
        
        if cache_dir.exists() and any(cache_dir.iterdir()):
            # Model has been downloaded
            cache_size = sum(f.stat().st_size for f in cache_dir.rglob('*') if f.is_file()) / (1024 * 1024)
            return True, models, f"Fully configured (model cached: {cache_size:.0f} MB)"
        else:
            # Package installed but model will download on first use
            return True, models, "Package installed (model will download on first use, ~700MB)"
            
    except Exception as e:
        return False, [], f"Error: {str(e)}"


def get_model_metadata(model_name: str) -> Dict:
    """Get metadata about a specific model from config files."""
    # Check image_describer_config.json
    config_path = Path("scripts/image_describer_config.json")
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                models_info = config.get('available_models', {})
                if model_name in models_info:
                    return models_info[model_name]
        except:
            pass
    
    return {}


def print_status_line(provider_name: str, available: bool, models: List[str], message: str, verbose: bool = False):
    """Print a formatted status line for a provider."""
    if available:
        icon = f"{Fore.GREEN}[OK]{Style.RESET_ALL}" if COLORS_AVAILABLE else "[OK]"
        status_color = Fore.GREEN if COLORS_AVAILABLE else ""
    else:
        icon = f"{Fore.RED}[--]{Style.RESET_ALL}" if COLORS_AVAILABLE else "[--]"
        status_color = Fore.RED if COLORS_AVAILABLE else ""
    
    print(f"\n{Style.BRIGHT}{provider_name}{Style.RESET_ALL}")
    print(f"  {icon} Status: {status_color}{message}{Style.RESET_ALL}")
    
    if available and models:
        print(f"  Models: {len(models)} available")
        for model in models:
            metadata = get_model_metadata(model)
            if verbose and metadata:
                size = metadata.get('size', 'unknown')
                desc = metadata.get('description', '')
                print(f"    • {model} ({size})")
                if desc:
                    print(f"      {desc}")
            else:
                print(f"    • {model}")
    elif not available:
        # Show installation instructions
        if "ollama service" in message.lower():
            print(f"  {Fore.YELLOW}->{Style.RESET_ALL} Install Ollama: https://ollama.ai")
            print(f"    Then run: ollama serve")
        elif "api key" in message.lower():
            print(f"  {Fore.YELLOW}->{Style.RESET_ALL} Add OpenAI API key to 'openai.txt' or OPENAI_API_KEY env var")
        elif "transformers" in message.lower():
            print(f"  {Fore.YELLOW}->{Style.RESET_ALL} Install: pip install transformers torch")
        elif "onnx" in message.lower():
            print(f"  {Fore.YELLOW}->{Style.RESET_ALL} Install: pip install onnxruntime")
            print(f"    Download models: run models/download_onnx_models.bat")
        elif "groundingdino" in message.lower():
            print(f"  {Fore.YELLOW}->{Style.RESET_ALL} Install: run models/install_groundingdino.bat")
            print(f"    This will install the package and download model files")


def get_recommendations(all_status: Dict) -> List[str]:
    """Generate recommendations based on current status."""
    recommendations = []
    
    # Check if Ollama is available
    if 'ollama' in all_status:
        if all_status['ollama']['available']:
            if len(all_status['ollama']['models']) == 0:
                recommendations.append("Install a recommended Ollama model:")
                recommendations.append("  ollama pull llava:7b        # Good balance (4.7GB)")
                recommendations.append("  ollama pull moondream       # Fastest (1.7GB)")
                recommendations.append("  ollama pull llama3.2-vision # Most accurate (7.5GB)")
            else:
                recommendations.append(f"[OK] Ollama is ready with {len(all_status['ollama']['models'])} models")
        else:
            recommendations.append("Install Ollama for local AI models: https://ollama.ai")
    
    # Check if OpenAI is available
    if 'openai' in all_status and not all_status['openai']['available']:
        recommendations.append("Optional: Configure OpenAI for cloud-based models")
    
    # Check if YOLO is available
    if 'onnx' in all_status and not all_status['onnx']['available']:
        recommendations.append("Optional: Install YOLO for enhanced object detection")
        recommendations.append("  pip install ultralytics")
    
    # Check if GroundingDINO is available
    if 'groundingdino' in all_status and not all_status['groundingdino']['available']:
        recommendations.append("Optional: Install GroundingDINO for advanced object detection")
        recommendations.append("  Run: models/install_groundingdino.bat")
    
    return recommendations


def main():
    parser = argparse.ArgumentParser(
        description='Check status of all AI models and providers',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m models.check_models                    # Check all providers
  python -m models.check_models --provider ollama  # Check only Ollama
  python -m models.check_models --verbose          # Show detailed model info
  python -m models.check_models --json             # Output as JSON
        """
    )
    parser.add_argument(
        '--provider',
        choices=['ollama', 'ollama-cloud', 'openai', 'huggingface', 'onnx', 'copilot', 'groundingdino'],
        help='Check only a specific provider'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed model information'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON (for scripting)'
    )
    
    args = parser.parse_args()
    
    # Check all providers
    providers = {
        'ollama': ('Ollama (Local Models)', check_ollama_status),
        'ollama-cloud': ('Ollama Cloud', check_ollama_cloud_status),
        'openai': ('OpenAI', check_openai_status),
        'huggingface': ('HuggingFace', check_huggingface_status),
        'onnx': ('ONNX / Enhanced YOLO', check_onnx_status),
        'copilot': ('Copilot+ PC (NPU)', check_copilot_status),
        'groundingdino': ('GroundingDINO (Object Detection)', check_groundingdino_status),
    }
    
    # Filter to specific provider if requested
    if args.provider:
        providers = {args.provider: providers[args.provider]}
    
    all_status = {}
    
    if not args.json:
        print(f"{Style.BRIGHT}=== Image Description Toolkit - Model Status ==={Style.RESET_ALL}")
        if not COLORS_AVAILABLE:
            print("(Install colorama for colored output: pip install colorama)\n")
    
    for provider_key, (provider_name, check_func) in providers.items():
        available, models, message = check_func()
        
        all_status[provider_key] = {
            'available': available,
            'models': models,
            'message': message
        }
        
        if not args.json:
            print_status_line(provider_name, available, models, message, args.verbose)
    
    if args.json:
        # Output as JSON for scripting
        print(json.dumps(all_status, indent=2))
    else:
        # Show recommendations
        print(f"\n{Style.BRIGHT}=== Recommendations ==={Style.RESET_ALL}")
        recommendations = get_recommendations(all_status)
        for rec in recommendations:
            if rec.startswith('  '):
                print(f"  {Fore.CYAN}{rec}{Style.RESET_ALL}")
            else:
                print(f"  • {rec}")
        
        print()


if __name__ == "__main__":
    main()
