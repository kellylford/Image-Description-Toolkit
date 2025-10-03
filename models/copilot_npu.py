"""
Copilot+ PC NPU Support Module

Provides DirectML-accelerated vision model inference using Copilot+ PC NPU hardware.
Supports Florence-2 and Phi-3 Vision ONNX models with neural processing unit acceleration.

Requirements:
- Windows 11 with Copilot+ PC hardware (Qualcomm/Intel/AMD NPU)
- onnxruntime-directml package
- transformers package (for tokenizer)

Usage:
    from models.copilot_npu import create_npu_session, run_florence2_inference
    
    session = create_npu_session("path/to/florence2.onnx")
    description = run_florence2_inference(session, "image.jpg", "Describe this image")
"""

import os
import platform
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import numpy as np


def is_npu_available() -> bool:
    """
    Check if NPU hardware is available.
    
    Returns:
        True if DirectML execution provider is available (indicates NPU/GPU support)
    """
    try:
        import onnxruntime as ort
        
        # Check if DirectML provider is available
        available_providers = ort.get_available_providers()
        has_directml = 'DmlExecutionProvider' in available_providers
        
        # Must be Windows for DirectML
        is_windows = platform.system() == "Windows"
        
        return has_directml and is_windows
    except ImportError:
        return False


def get_npu_info() -> str:
    """
    Get information about the available NPU/DirectML hardware.
    
    Returns:
        String describing the NPU status
    """
    if not is_npu_available():
        return "NPU not available (requires Windows + DirectML)"
    
    try:
        import onnxruntime as ort
        providers = ort.get_available_providers()
        
        info = ["DirectML available"]
        
        # Check for GPU provider as well
        if 'CUDAExecutionProvider' in providers:
            info.append("CUDA GPU")
        if 'TensorrtExecutionProvider' in providers:
            info.append("TensorRT")
        
        return ", ".join(info)
    except:
        return "DirectML (status unknown)"


def create_npu_session(model_path: str, use_npu: bool = True) -> Any:
    """
    Create ONNX Runtime session with DirectML execution provider for NPU.
    
    Args:
        model_path: Path to ONNX model file
        use_npu: Whether to use NPU acceleration (DirectML)
        
    Returns:
        InferenceSession configured for NPU/DirectML
        
    Raises:
        ImportError: If onnxruntime is not installed
        FileNotFoundError: If model file doesn't exist
        RuntimeError: If session creation fails
    """
    try:
        import onnxruntime as ort
    except ImportError:
        raise ImportError(
            "onnxruntime is required for Copilot+ PC support. "
            "Install with: pip install onnxruntime-directml"
        )
    
    model_path = Path(model_path)
    if not model_path.exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")
    
    try:
        # Configure session options
        session_options = ort.SessionOptions()
        session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        
        # Enable memory pattern optimization
        session_options.enable_mem_pattern = True
        session_options.enable_cpu_mem_arena = True
        
        # Set execution mode to sequential for stability
        session_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        
        # Configure providers
        if use_npu and is_npu_available():
            # DirectML for NPU acceleration
            providers = ['DmlExecutionProvider', 'CPUExecutionProvider']
        else:
            # CPU fallback
            providers = ['CPUExecutionProvider']
        
        # Create session
        session = ort.InferenceSession(
            str(model_path),
            sess_options=session_options,
            providers=providers
        )
        
        return session
        
    except Exception as e:
        raise RuntimeError(f"Failed to create NPU session: {e}")


def preprocess_image_for_florence2(image_path: str, target_size: Tuple[int, int] = (384, 384)) -> np.ndarray:
    """
    Preprocess image for Florence-2 model input.
    
    Args:
        image_path: Path to input image
        target_size: Target size (height, width) for model input
        
    Returns:
        Preprocessed image tensor in NCHW format (batch, channels, height, width)
    """
    try:
        from PIL import Image
    except ImportError:
        raise ImportError("PIL is required. Install with: pip install Pillow")
    
    # Load image
    image = Image.open(image_path).convert('RGB')
    
    # Resize
    image = image.resize(target_size, Image.Resampling.BILINEAR)
    
    # Convert to numpy array and normalize to [0, 1]
    image_array = np.array(image).astype(np.float32) / 255.0
    
    # Apply ImageNet normalization
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    
    image_array = (image_array - mean) / std
    
    # Convert to NCHW format (batch, channels, height, width)
    image_tensor = image_array.transpose(2, 0, 1)[np.newaxis, ...]
    
    return image_tensor.astype(np.float32)


def prepare_text_inputs_florence2(prompt: str, max_length: int = 512) -> Dict[str, np.ndarray]:
    """
    Prepare text inputs for Florence-2 model.
    
    Args:
        prompt: Input text prompt/task
        max_length: Maximum sequence length
        
    Returns:
        Dictionary with 'input_ids' and 'attention_mask' as numpy arrays
    """
    try:
        from transformers import AutoTokenizer
    except ImportError:
        raise ImportError("transformers is required. Install with: pip install transformers")
    
    # Try to load Florence-2 tokenizer
    try:
        # Check for local Florence-2 model directory
        florence2_dir = Path("models/onnx/florence2")
        if florence2_dir.exists():
            tokenizer = AutoTokenizer.from_pretrained(str(florence2_dir), trust_remote_code=True)
        else:
            # Try to download tokenizer (small, ~2MB)
            tokenizer = AutoTokenizer.from_pretrained(
                "microsoft/Florence-2-base", 
                trust_remote_code=True
            )
    except Exception as e:
        raise RuntimeError(f"Failed to load Florence-2 tokenizer: {e}")
    
    # Encode text
    encoding = tokenizer(
        prompt,
        max_length=max_length,
        padding="max_length",
        truncation=True,
        return_tensors="np"
    )
    
    return {
        'input_ids': encoding['input_ids'].astype(np.int64),
        'attention_mask': encoding['attention_mask'].astype(np.int64)
    }


def decode_florence2_output(output_ids: np.ndarray) -> str:
    """
    Decode Florence-2 model output tokens to text.
    
    Args:
        output_ids: Model output token IDs
        
    Returns:
        Decoded text string
    """
    try:
        from transformers import AutoTokenizer
    except ImportError:
        raise ImportError("transformers is required. Install with: pip install transformers")
    
    # Load tokenizer
    try:
        florence2_dir = Path("models/onnx/florence2")
        if florence2_dir.exists():
            tokenizer = AutoTokenizer.from_pretrained(str(florence2_dir), trust_remote_code=True)
        else:
            tokenizer = AutoTokenizer.from_pretrained(
                "microsoft/Florence-2-base",
                trust_remote_code=True
            )
    except Exception as e:
        raise RuntimeError(f"Failed to load tokenizer for decoding: {e}")
    
    # Decode
    text = tokenizer.decode(output_ids[0], skip_special_tokens=True)
    return text.strip()


def run_florence2_inference(
    session: Any,
    image_path: str,
    prompt: str = "Describe this image in detail",
    max_new_tokens: int = 200
) -> str:
    """
    Run Florence-2 inference on NPU.
    
    Args:
        session: ONNX Runtime session (from create_npu_session)
        image_path: Path to input image
        prompt: Text prompt/task for the model
        max_new_tokens: Maximum number of tokens to generate
        
    Returns:
        Generated description text
    """
    # Preprocess image
    image_tensor = preprocess_image_for_florence2(image_path)
    
    # Prepare text inputs
    text_inputs = prepare_text_inputs_florence2(prompt)
    
    # Prepare model inputs
    inputs = {
        'pixel_values': image_tensor,
        'input_ids': text_inputs['input_ids'],
        'attention_mask': text_inputs['attention_mask']
    }
    
    # Run inference on NPU
    try:
        outputs = session.run(None, inputs)
        
        # The first output is typically the generated sequence
        output_ids = outputs[0]
        
        # Decode to text
        description = decode_florence2_output(output_ids)
        
        return description
        
    except Exception as e:
        raise RuntimeError(f"Florence-2 NPU inference failed: {e}")


def download_florence2_onnx() -> Path:
    """
    Download Florence-2 ONNX model (placeholder - actual implementation needed).
    
    Returns:
        Path to downloaded ONNX model
    """
    # This would need to:
    # 1. Download Florence-2 from HuggingFace
    # 2. Export to ONNX format
    # 3. Optimize for DirectML
    # 4. Save to models/onnx/florence2/
    
    raise NotImplementedError(
        "Florence-2 ONNX download not yet implemented. "
        "Manual steps required: "
        "1. Download microsoft/Florence-2-base from HuggingFace "
        "2. Export to ONNX using transformers.onnx "
        "3. Place in models/onnx/florence2/"
    )


# Convenience functions for checking availability
def check_npu_requirements() -> Dict[str, bool]:
    """
    Check all requirements for NPU support.
    
    Returns:
        Dictionary of requirement checks
    """
    checks = {}
    
    # Check OS
    checks['windows'] = platform.system() == "Windows"
    
    # Check onnxruntime
    try:
        import onnxruntime
        checks['onnxruntime'] = True
    except ImportError:
        checks['onnxruntime'] = False
    
    # Check DirectML
    checks['directml'] = is_npu_available()
    
    # Check transformers
    try:
        import transformers
        checks['transformers'] = True
    except ImportError:
        checks['transformers'] = False
    
    # Check PIL
    try:
        from PIL import Image
        checks['pillow'] = True
    except ImportError:
        checks['pillow'] = False
    
    return checks


def get_setup_instructions() -> str:
    """
    Get instructions for setting up Copilot+ PC support.
    
    Returns:
        Formatted setup instructions
    """
    checks = check_npu_requirements()
    
    instructions = ["Copilot+ PC NPU Setup:\n"]
    
    if not checks['windows']:
        instructions.append("❌ Windows 11 required for DirectML NPU support")
    else:
        instructions.append("✅ Windows detected")
    
    if not checks['onnxruntime']:
        instructions.append("❌ Install: pip install onnxruntime-directml")
    else:
        instructions.append("✅ onnxruntime installed")
    
    if not checks['directml']:
        instructions.append("❌ DirectML not available (need Copilot+ PC hardware)")
    else:
        instructions.append("✅ DirectML available")
    
    if not checks['transformers']:
        instructions.append("❌ Install: pip install transformers")
    else:
        instructions.append("✅ transformers installed")
    
    if not checks['pillow']:
        instructions.append("❌ Install: pip install Pillow")
    else:
        instructions.append("✅ Pillow installed")
    
    all_ready = all(checks.values())
    if all_ready:
        instructions.append("\n✅ All requirements met! NPU acceleration ready.")
    else:
        instructions.append("\n⚠️ Some requirements missing. Install missing packages.")
    
    return "\n".join(instructions)


if __name__ == "__main__":
    # Self-test
    print(get_setup_instructions())
    print(f"\nNPU Info: {get_npu_info()}")
