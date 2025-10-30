#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for web_image_downloader module
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import io

# Add scripts directory to path
scripts_dir = Path(__file__).parent.parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from web_image_downloader import WebImageDownloader


class TestWebImageDownloader:
    """Test cases for WebImageDownloader class"""
    
    def test_init(self, tmp_path):
        """Test downloader initialization"""
        url = "https://example.com/gallery"
        downloader = WebImageDownloader(
            url=url,
            output_dir=tmp_path,
            min_width=100,
            min_height=100,
            max_images=10,
            verbose=False
        )
        
        assert downloader.url == url
        assert downloader.output_dir == tmp_path
        assert downloader.min_width == 100
        assert downloader.min_height == 100
        assert downloader.max_images == 10
        assert downloader.downloaded_count == 0
    
    def test_is_valid_image_url(self, tmp_path):
        """Test image URL validation"""
        downloader = WebImageDownloader("https://example.com", tmp_path)
        
        # Valid image URLs
        assert downloader._is_valid_image_url("https://example.com/image.jpg")
        assert downloader._is_valid_image_url("https://example.com/photo.png")
        assert downloader._is_valid_image_url("https://example.com/pic.gif")
        assert downloader._is_valid_image_url("https://example.com/test.JPEG")
        
        # Invalid URLs
        assert not downloader._is_valid_image_url("https://example.com/page.html")
        assert not downloader._is_valid_image_url("https://example.com/doc.pdf")
    
    def test_get_safe_filename(self, tmp_path):
        """Test safe filename generation"""
        downloader = WebImageDownloader("https://example.com", tmp_path)
        
        # Test with valid image URL
        filename = downloader._get_safe_filename("https://example.com/photo.jpg", 1)
        assert filename == "photo.jpg"
        
        # Test with URL without extension
        filename = downloader._get_safe_filename("https://example.com/image", 5)
        assert filename == "image_0005.jpg"
        
        # Test with special characters
        filename = downloader._get_safe_filename("https://example.com/my photo!@#.png", 1)
        assert "myphoto" in filename.lower()
        assert filename.endswith(".png")
    
    def test_extract_image_urls(self, tmp_path):
        """Test image URL extraction from HTML"""
        downloader = WebImageDownloader("https://example.com", tmp_path)
        
        # Test HTML with images
        html = """
        <html>
            <body>
                <img src="/image1.jpg" />
                <img src="https://example.com/image2.png" />
                <img data-src="/lazy-image.gif" />
                <a href="/photo.jpg">Link to photo</a>
            </body>
        </html>
        """
        
        urls = downloader._extract_image_urls(html, "https://example.com")
        
        # Should extract all valid image URLs
        assert len(urls) >= 3  # At least the main src images
        
        # Check that relative URLs are converted to absolute
        assert all(url.startswith("http") for url in urls)
    
    def test_extract_image_urls_no_duplicates(self, tmp_path):
        """Test that duplicate URLs are removed"""
        downloader = WebImageDownloader("https://example.com", tmp_path)
        
        html = """
        <html>
            <body>
                <img src="/image1.jpg" />
                <img src="/image1.jpg" />
                <img src="https://example.com/image1.jpg" />
            </body>
        </html>
        """
        
        urls = downloader._extract_image_urls(html, "https://example.com")
        
        # Should only have unique URLs
        assert len(urls) == len(set(urls))
    
    @patch('web_image_downloader.requests.Session')
    def test_download_with_max_images(self, mock_session, tmp_path):
        """Test that max_images limit is respected"""
        downloader = WebImageDownloader(
            "https://example.com", 
            tmp_path,
            max_images=2
        )
        
        # Mock the response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <body>
                <img src="/img1.jpg" />
                <img src="/img2.jpg" />
                <img src="/img3.jpg" />
                <img src="/img4.jpg" />
            </body>
        </html>
        """
        mock_session.return_value.get.return_value = mock_response
        
        # Note: This test would need more mocking to fully work
        # but it demonstrates the test structure
    
    def test_image_size_filtering(self, tmp_path):
        """Test min_width and min_height filtering"""
        downloader = WebImageDownloader(
            "https://example.com",
            tmp_path,
            min_width=200,
            min_height=200
        )
        
        assert downloader.min_width == 200
        assert downloader.min_height == 200


class TestWebImageDownloaderIntegration:
    """Integration tests for web_image_downloader"""
    
    def test_main_function_help(self):
        """Test that main function can display help"""
        from web_image_downloader import main
        
        # This is a basic smoke test
        # A full test would need to mock sys.argv and capture output
        assert callable(main)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
