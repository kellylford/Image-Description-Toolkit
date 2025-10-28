#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Image Description Toolkit - Web Image Downloader

This script downloads images from a web page and saves them to a directory
for processing by the workflow system.

Usage:
    python web_image_downloader.py <url> <output_dir> [options]
    
Examples:
    python web_image_downloader.py https://example.com/gallery photos
    python web_image_downloader.py https://example.com/page output --min-size 100x100
"""

import sys
import os
import argparse
import requests
from pathlib import Path
from urllib.parse import urljoin, urlparse
from typing import List, Set, Optional, Tuple
import logging
import time
import hashlib

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: BeautifulSoup4 not installed")
    print("Install with: pip install beautifulsoup4")
    sys.exit(1)

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow not installed")
    print("Install with: pip install Pillow")
    sys.exit(1)


class WebImageDownloader:
    """Downloads images from web pages"""
    
    def __init__(self, url: str, output_dir: Path, 
                 min_width: int = 0, min_height: int = 0,
                 max_images: Optional[int] = None,
                 user_agent: str = None,
                 timeout: int = 30,
                 verbose: bool = False):
        """
        Initialize the web image downloader
        
        Args:
            url: URL of the web page to download images from
            output_dir: Directory to save downloaded images
            min_width: Minimum width of images to download (0 = no limit)
            min_height: Minimum height of images to download (0 = no limit)
            max_images: Maximum number of images to download (None = no limit)
            user_agent: Custom user agent string
            timeout: Request timeout in seconds
            verbose: Enable verbose logging
        """
        self.url = url
        self.output_dir = Path(output_dir)
        self.min_width = min_width
        self.min_height = min_height
        self.max_images = max_images
        self.timeout = timeout
        self.verbose = verbose
        
        # Setup logging
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)
        
        # Setup session with headers
        self.session = requests.Session()
        if user_agent:
            self.session.headers.update({'User-Agent': user_agent})
        else:
            # Use a common browser user agent
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
        
        # Track downloaded images to avoid duplicates
        self.downloaded_hashes: Set[str] = set()
        self.downloaded_count = 0
        
        # Supported image extensions
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif'}
        
    def _get_image_hash(self, image_data: bytes) -> str:
        """Calculate hash of image data to detect duplicates"""
        return hashlib.md5(image_data).hexdigest()
    
    def _is_valid_image_url(self, url: str) -> bool:
        """Check if URL appears to be an image"""
        parsed = urlparse(url.lower())
        path = parsed.path
        # Check if path has image extension
        return any(path.endswith(ext) for ext in self.image_extensions)
    
    def _get_safe_filename(self, url: str, index: int) -> str:
        """Generate a safe filename from URL"""
        parsed = urlparse(url)
        path = parsed.path
        
        # Try to extract filename from URL
        filename = os.path.basename(path)
        
        # If no filename or not an image extension, create one
        if not filename or not any(filename.lower().endswith(ext) for ext in self.image_extensions):
            # Get extension from Content-Type or default to .jpg
            filename = f"image_{index:04d}.jpg"
        
        # Remove any problematic characters
        filename = "".join(c for c in filename if c.isalnum() or c in ('_', '-', '.'))
        
        return filename
    
    def _download_image(self, img_url: str, index: int) -> Optional[Path]:
        """
        Download a single image
        
        Returns:
            Path to downloaded image if successful, None otherwise
        """
        try:
            self.logger.debug(f"Downloading image {index}: {img_url}")
            
            # Download image
            response = self.session.get(img_url, timeout=self.timeout, stream=True)
            response.raise_for_status()
            
            # Read image data
            image_data = response.content
            
            # Check for duplicates
            img_hash = self._get_image_hash(image_data)
            if img_hash in self.downloaded_hashes:
                self.logger.debug(f"Skipping duplicate image: {img_url}")
                return None
            
            # Validate it's actually an image
            try:
                img = Image.open(requests.compat.BytesIO(image_data))
                width, height = img.size
                
                # Check size requirements
                if self.min_width > 0 and width < self.min_width:
                    self.logger.debug(f"Skipping image (width {width} < {self.min_width}): {img_url}")
                    return None
                if self.min_height > 0 and height < self.min_height:
                    self.logger.debug(f"Skipping image (height {height} < {self.min_height}): {img_url}")
                    return None
                    
                self.logger.debug(f"Image dimensions: {width}x{height}")
                
            except Exception as e:
                self.logger.warning(f"Failed to validate image {img_url}: {e}")
                return None
            
            # Save image
            filename = self._get_safe_filename(img_url, index)
            output_path = self.output_dir / filename
            
            # Ensure unique filename
            counter = 1
            while output_path.exists():
                name, ext = os.path.splitext(filename)
                output_path = self.output_dir / f"{name}_{counter}{ext}"
                counter += 1
            
            # Write image to file
            with open(output_path, 'wb') as f:
                f.write(image_data)
            
            # Mark as downloaded
            self.downloaded_hashes.add(img_hash)
            self.downloaded_count += 1
            
            self.logger.info(f"Downloaded: {output_path.name} ({width}x{height})")
            return output_path
            
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Failed to download {img_url}: {e}")
            return None
        except Exception as e:
            self.logger.warning(f"Error processing {img_url}: {e}")
            return None
    
    def _extract_image_urls(self, html_content: str, base_url: str) -> List[str]:
        """
        Extract image URLs from HTML content
        
        Args:
            html_content: HTML content to parse
            base_url: Base URL for resolving relative URLs
            
        Returns:
            List of absolute image URLs
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        image_urls = []
        
        # Find all img tags
        for img in soup.find_all('img'):
            # Get src or data-src (for lazy loading)
            src = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
            
            if src:
                # Convert to absolute URL
                absolute_url = urljoin(base_url, src)
                
                # Add if it looks like an image
                if self._is_valid_image_url(absolute_url):
                    image_urls.append(absolute_url)
                    self.logger.debug(f"Found image URL: {absolute_url}")
        
        # Also check for picture elements
        for picture in soup.find_all('picture'):
            for source in picture.find_all('source'):
                srcset = source.get('srcset')
                if srcset:
                    # Parse srcset (can contain multiple URLs)
                    urls = [url.strip().split()[0] for url in srcset.split(',')]
                    for url in urls:
                        absolute_url = urljoin(base_url, url)
                        if self._is_valid_image_url(absolute_url):
                            image_urls.append(absolute_url)
                            self.logger.debug(f"Found image URL in picture: {absolute_url}")
        
        # Also check for links to images
        for link in soup.find_all('a'):
            href = link.get('href')
            if href and self._is_valid_image_url(href):
                absolute_url = urljoin(base_url, href)
                image_urls.append(absolute_url)
                self.logger.debug(f"Found image URL in link: {absolute_url}")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in image_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)
        
        return unique_urls
    
    def download(self) -> Tuple[int, int]:
        """
        Download images from the web page
        
        Returns:
            Tuple of (successful_downloads, failed_downloads)
        """
        self.logger.info(f"Starting image download from: {self.url}")
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Fetch the web page
            self.logger.info(f"Fetching web page...")
            response = self.session.get(self.url, timeout=self.timeout)
            response.raise_for_status()
            
            # Extract image URLs
            self.logger.info(f"Extracting image URLs...")
            image_urls = self._extract_image_urls(response.text, self.url)
            
            total_found = len(image_urls)
            self.logger.info(f"Found {total_found} potential image URLs")
            
            if total_found == 0:
                self.logger.warning("No images found on the page")
                return 0, 0
            
            # Download images
            successful = 0
            failed = 0
            
            for i, img_url in enumerate(image_urls, 1):
                # Check if we've reached max images
                if self.max_images and successful >= self.max_images:
                    self.logger.info(f"Reached maximum image limit ({self.max_images})")
                    break
                
                # Download the image
                result = self._download_image(img_url, i)
                
                if result:
                    successful += 1
                else:
                    failed += 1
                
                # Small delay to be respectful to the server
                if i < total_found:
                    time.sleep(0.5)
            
            self.logger.info(f"Download complete: {successful} successful, {failed} failed/skipped")
            return successful, failed
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to fetch web page: {e}")
            return 0, 0
        except Exception as e:
            self.logger.error(f"Error during download: {e}")
            return 0, 0


def main():
    """Main function for command-line usage"""
    parser = argparse.ArgumentParser(
        description="Download images from a web page",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python web_image_downloader.py https://example.com/gallery photos
  python web_image_downloader.py https://example.com/page output --min-size 200x200
  python web_image_downloader.py https://example.com/page output --max-images 50
        """
    )
    
    parser.add_argument(
        "url",
        help="URL of the web page to download images from"
    )
    
    parser.add_argument(
        "output_dir",
        help="Directory to save downloaded images"
    )
    
    parser.add_argument(
        "--min-size",
        help="Minimum image size in format WIDTHxHEIGHT (e.g., 200x200)"
    )
    
    parser.add_argument(
        "--max-images",
        type=int,
        help="Maximum number of images to download"
    )
    
    parser.add_argument(
        "--user-agent",
        help="Custom user agent string"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Request timeout in seconds (default: 30)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Parse min-size if provided
    min_width = 0
    min_height = 0
    if args.min_size:
        try:
            parts = args.min_size.lower().split('x')
            if len(parts) == 2:
                min_width = int(parts[0])
                min_height = int(parts[1])
            else:
                print(f"ERROR: Invalid min-size format. Use WIDTHxHEIGHT (e.g., 200x200)")
                return 1
        except ValueError:
            print(f"ERROR: Invalid min-size format. Use WIDTHxHEIGHT (e.g., 200x200)")
            return 1
    
    # Create downloader and run
    downloader = WebImageDownloader(
        url=args.url,
        output_dir=Path(args.output_dir),
        min_width=min_width,
        min_height=min_height,
        max_images=args.max_images,
        user_agent=args.user_agent,
        timeout=args.timeout,
        verbose=args.verbose
    )
    
    successful, failed = downloader.download()
    
    if successful > 0:
        print(f"\nSuccess! Downloaded {successful} images to {args.output_dir}")
        return 0
    else:
        print(f"\nFailed to download any images")
        return 1


if __name__ == "__main__":
    sys.exit(main())
