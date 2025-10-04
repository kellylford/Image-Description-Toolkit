"""
Convert BLIP model to ONNX for Copilot+ PC NPU acceleration

This script converts the BLIP image captioning model to ONNX format
for use with DirectML NPU acceleration on Copilot+ PCs.

REQUIREMENTS:
- Python 3.11 (transformers doesn't support Python 3.13 yet)
- optimum[exporters] and transformers packages

USAGE:
    # Create Python 3.11 environment
    py -3.11 -m venv .venv311
    .venv311\Scripts\activate
    
    # Install dependencies
    pip install optimum[exporters] transformers torch
    
    # Run conversion
    python models/convert_blip_to_onnx.py
    
    # Model will be saved to models/onnx/blip/

NOTE: After conversion, you can use the ONNX model in Python 3.13
      with onnxruntime-directml (no transformers needed at runtime)
"""

import sys
from pathlib import Path

def check_requirements():
    """Check if required packages are installed"""
    try:
        import transformers
        import optimum
        print(f"✓ transformers version: {transformers.__version__}")
        print(f"✓ optimum version: {optimum.__version__}")
    except ImportError as e:
        print(f"ERROR: Missing required package: {e}")
        print("\nPlease install:")
        print("  pip install optimum[exporters] transformers torch")
        sys.exit(1)
    
    # Check Python version
    if sys.version_info >= (3, 13):
        print("\nWARNING: You are using Python 3.13")
        print("transformers library doesn't fully support Python 3.13 yet")
        print("Recommended: Use Python 3.11 for this conversion script")
        print("\nTo create Python 3.11 environment:")
        print("  py -3.11 -m venv .venv311")
        print("  .venv311\\Scripts\\activate")
        print("  pip install optimum[exporters] transformers torch")
        response = input("\nContinue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(0)

def convert_blip():
    """Convert BLIP model to ONNX format"""
    from optimum.exporters.onnx import main_export
    from pathlib import Path
    
    # Model to convert
    model_id = "Salesforce/blip-image-captioning-base"
    output_dir = Path(__file__).parent / "onnx" / "blip"
    
    print(f"\n{'='*80}")
    print(f"Converting BLIP to ONNX")
    print(f"{'='*80}")
    print(f"Model: {model_id}")
    print(f"Output: {output_dir}")
    print(f"\nThis will download ~990MB and may take 5-10 minutes...")
    print()
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Convert model
        main_export(
            model_name_or_path=model_id,
            output=str(output_dir),
            task="image-to-text-with-past"
        )
        
        print(f"\n{'='*80}")
        print(f"SUCCESS! BLIP model converted to ONNX")
        print(f"{'='*80}")
        print(f"\nModel files saved to: {output_dir}")
        print(f"\nFiles created:")
        for file in output_dir.glob("*"):
            size_mb = file.stat().st_size / (1024 * 1024)
            print(f"  - {file.name} ({size_mb:.1f} MB)")
        
        print(f"\n{'='*80}")
        print("Next Steps:")
        print(f"{'='*80}")
        print("1. Deactivate Python 3.11 environment (if used)")
        print("2. Return to Python 3.13 environment")
        print("3. Install ONNX Runtime DirectML:")
        print("     pip install onnxruntime-directml")
        print("4. Run ImageDescriber and select 'Copilot+ PC' provider")
        print(f"{'='*80}")
        
    except Exception as e:
        print(f"\nERROR during conversion: {e}")
        print("\nCommon issues:")
        print("  - Out of memory: Close other applications")
        print("  - Network error: Check internet connection")
        print("  - Python 3.13: Use Python 3.11 instead")
        sys.exit(1)

def main():
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║            BLIP to ONNX Conversion for Copilot+ PC NPU                     ║
╚════════════════════════════════════════════════════════════════════════════╝
""")
    
    check_requirements()
    convert_blip()

if __name__ == "__main__":
    main()
