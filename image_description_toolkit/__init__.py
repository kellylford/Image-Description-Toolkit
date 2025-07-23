"""
Image Description Toolkit

An AI-powered toolkit for generating descriptive text from images using local language models via Ollama.
"""

__version__ = "0.1.0"
__author__ = "kellylford"
__description__ = "Experimental tools for image description interaction."

# Main workflow imports
from .workflow import main as workflow_main

# Core component imports  
from .image_describer import ImageDescriber, get_default_prompt_style
from .video_frame_extractor import VideoFrameExtractor
from .convert_image import convert_heic_to_jpg
from .descriptions_to_html import main as generate_html_report

__all__ = [
    'workflow_main',
    'ImageDescriber',
    'get_default_prompt_style',
    'VideoFrameExtractor',
    'convert_heic_to_jpg', 
    'generate_html_report'
]