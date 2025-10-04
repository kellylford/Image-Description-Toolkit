#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HEIC to JPG Converter

This script converts HEIC/HEIF image files to JPG format.
Supports both individual files and batch conversion of directories.

Part of the ImageDescriber toolkit for AI-powered image analysis.
Use this tool to convert HEIC images to JPG format before processing
with the main ImageDescriber script.
"""

import sys
import os
import argparse
import logging
import time
from pathlib import Path
from PIL import Image
from datetime import datetime

# Set UTF-8 encoding for console output on Windows
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
import pillow_heif

# Register HEIF opener with PIL
pillow_heif.register_heif_opener()

# Set up logging
logger = logging.getLogger(__name__)

def setup_logging(log_dir=None, verbose=False):
    """Setup logging for the converter"""
    global logger
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Set logging level
    level = logging.DEBUG if verbose else logging.INFO
    logger.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler if log_dir is provided
    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = log_dir / f"convert_image_{timestamp}.log"
        
        file_handler = logging.FileHandler(log_filename, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        logger.info(f"Convert Image log file: {log_filename.absolute()}")


def convert_heic_to_jpg(input_path, output_path=None, quality=95, keep_metadata=True):
    """
    Convert a single HEIC file to JPG format.
    
    Args:
        input_path: Path to the input HEIC file
        output_path: Path for the output JPG file (optional)
        quality: JPEG quality (1-100, default 95)
        keep_metadata: Whether to preserve metadata (default True)
    
    Returns:
        bool: True if conversion successful, False otherwise
    """
    try:
        input_path = Path(input_path)
        
        # Generate output path if not provided
        if output_path is None:
            output_path = input_path.with_suffix('.jpg')
        else:
            output_path = Path(output_path)
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Open and convert the image
        with Image.open(input_path) as image:
            # Convert to RGB if necessary (HEIC can have different color modes)
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Save as JPEG with specified quality
            save_kwargs = {
                'format': 'JPEG',
                'quality': quality,
                'optimize': True
            }
            
            # Preserve metadata if requested
            if keep_metadata and hasattr(image, 'info'):
                save_kwargs['exif'] = image.info.get('exif', b'')
            
            image.save(output_path, **save_kwargs)
        
        # Preserve file modification time from source for chronological sorting
        try:
            source_stat = os.stat(input_path)
            os.utime(output_path, (source_stat.st_atime, source_stat.st_mtime))
        except OSError as e:
            logger.debug(f"Could not preserve timestamp on {output_path}: {e}")
        
        logger.info(f"Successfully converted: {input_path.name} -> {output_path.name}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to convert {input_path}: {e}")
        return False


def convert_directory(directory_path, output_directory=None, recursive=False, quality=95, keep_metadata=True):
    """
    Convert all HEIC files in a directory to JPG format.
    
    Args:
        directory_path: Path to the directory containing HEIC files
        output_directory: Output directory (default: workflow_output/converted_images/)
        recursive: Whether to process subdirectories recursively
        quality: JPEG quality (1-100, default 95)
        keep_metadata: Whether to preserve metadata (default True)
    
    Returns:
        tuple: (successful_count, failed_count)
    """
    directory_path = Path(directory_path)
    
    if not directory_path.exists():
        logger.error(f"Directory does not exist: {directory_path}")
        return 0, 0
    
    if not directory_path.is_dir():
        logger.error(f"Path is not a directory: {directory_path}")
        return 0, 0
    
    logger.info(f"Starting HEIC conversion in directory: {directory_path}")
    start_time = time.time()
    
    # Set up output directory
    if output_directory is None:
        # Use workflow output directory
        try:
            from workflow_utils import WorkflowConfig
            config = WorkflowConfig()
            output_directory = config.get_step_output_dir("image_conversion", create=True)
            logger.info(f"Using workflow output directory: {output_directory}")
        except ImportError:
            # Fallback if workflow_utils not available
            output_directory = directory_path / "converted"
            logger.info(f"Using fallback output directory: {output_directory}")
    else:
        output_directory = Path(output_directory)
        logger.info(f"Using specified output directory: {output_directory}")
    
    output_directory.mkdir(parents=True, exist_ok=True)
    
    # Find HEIC files
    pattern = "**/*.heic" if recursive else "*.heic"
    heic_files = list(directory_path.glob(pattern))
    
    # Also check for .HEIF extension
    heif_pattern = "**/*.heif" if recursive else "*.heif"
    heic_files.extend(directory_path.glob(heif_pattern))
    
    if not heic_files:
        logger.info(f"No HEIC/HEIF files found in {directory_path}")
        return 0, 0
    
    logger.info(f"Found {len(heic_files)} HEIC/HEIF files to convert")
    
    successful = 0
    failed = 0
    
    for i, heic_file in enumerate(heic_files, 1):
        logger.info(f"Converting file {i}/{len(heic_files)}: {heic_file.name}")
        
        # Preserve directory structure in output
        if recursive:
            relative_path = heic_file.relative_to(directory_path)
            output_file = output_directory / relative_path.with_suffix('.jpg')
        else:
            output_file = output_directory / heic_file.with_suffix('.jpg').name
        
        if convert_heic_to_jpg(heic_file, output_file, quality, keep_metadata):
            successful += 1
        else:
            failed += 1
    
    # Final statistics
    elapsed_time = time.time() - start_time
    
    logger.info("="*50)
    logger.info("CONVERSION SUMMARY")
    logger.info("="*50)
    logger.info(f"Total files processed: {len(heic_files)}")
    logger.info(f"Successful conversions: {successful}")
    logger.info(f"Failed conversions: {failed}")
    logger.info(f"Processing time: {elapsed_time:.2f} seconds")
    if len(heic_files) > 0:
        logger.info(f"Average time per file: {elapsed_time/len(heic_files):.2f} seconds")
    logger.info(f"Output directory: {output_directory}")
    logger.info("="*50)
    
    return successful, failed


def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(
        description="Convert HEIC/HEIF images to JPG format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ConvertImage.py photos/                    # Convert all HEIC files in photos/
  python ConvertImage.py photos/ --recursive        # Include subdirectories
  python ConvertImage.py photo.heic                 # Convert single file
  python ConvertImage.py photos/ --quality 85       # Lower quality, smaller files
  python ConvertImage.py photos/ --output converted/ # Custom output directory
        """
    )
    
    parser.add_argument(
        "input",
        help="Input HEIC file or directory containing HEIC files"
    )
    
    parser.add_argument(
        "--output", "-o",
        help="Output file or directory (default: creates 'converted' subdirectory for directories)"
    )
    
    parser.add_argument(
        "--recursive", "-r",
        action="store_true",
        help="Process subdirectories recursively"
    )
    
    parser.add_argument(
        "--quality", "-q",
        type=int,
        default=95,
        choices=range(1, 101),
        metavar="1-100",
        help="JPEG quality (1-100, default: 95)"
    )
    
    parser.add_argument(
        "--no-metadata",
        action="store_true",
        help="Don't preserve metadata in converted files"
    )
    
    parser.add_argument(
        "--log-dir",
        help="Directory for log files (default: auto-detect workflow directory)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Setup logging before any processing
    setup_logging(args.log_dir, args.verbose)
    
    input_path = Path(args.input)
    
    if not input_path.exists():
        logger.error(f"Input path does not exist: {input_path}")
        sys.exit(1)
    
    # Check if pillow-heif is properly installed
    try:
        # Test if HEIF support is available
        test_formats = Image.registered_extensions()
        if '.heic' not in test_formats and '.heif' not in test_formats:
            logger.warning("HEIF support may not be properly registered")
    except Exception as e:
        logger.warning(f"Issue with HEIF support: {e}")
    
    if input_path.is_file():
        # Convert single file
        if not input_path.suffix.lower() in ['.heic', '.heif']:
            logger.error(f"File is not a HEIC/HEIF file: {input_path}")
            sys.exit(1)
        
        output_file = args.output
        if output_file and Path(output_file).is_dir():
            output_file = Path(output_file) / input_path.with_suffix('.jpg').name
        
        success = convert_heic_to_jpg(
            input_path, 
            output_file, 
            args.quality, 
            not args.no_metadata
        )
        
        sys.exit(0 if success else 1)
    
    elif input_path.is_dir():
        # Convert directory
        successful, failed = convert_directory(
            input_path,
            args.output,
            args.recursive,
            args.quality,
            not args.no_metadata
        )
        
        sys.exit(0 if failed == 0 else 1)
    
    else:
        logger.error(f"Invalid input path: {input_path}")
        sys.exit(1)


if __name__ == "__main__":
    main()
