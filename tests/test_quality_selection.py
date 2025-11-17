"""Tests for quality selection functionality."""
import unittest
from downloader.discover import discover_media_url, _extract_quality_info
from bs4 import BeautifulSoup


class TestQualitySelection(unittest.TestCase):
    def test_single_source(self):
        """Test with single source tag."""
        html = '<video><source src="video.mp4"></video>'
        result = discover_media_url(html)
        self.assertEqual(result, "video.mp4")
    
    def test_multiple_sources_by_resolution(self):
        """Test selecting highest resolution from multiple sources."""
        html = '''
        <video>
            <source src="video_720p.mp4" data-width="1280" data-height="720" label="720p">
            <source src="video_1080p.mp4" data-width="1920" data-height="1080" label="1080p">
            <source src="video_480p.mp4" data-width="854" data-height="480" label="480p">
        </video>
        '''
        result = discover_media_url(html, prefer_highest_quality=True)
        self.assertEqual(result, "video_1080p.mp4")
    
    def test_multiple_sources_by_quality_label(self):
        """Test selecting by quality label (e.g., 1080p)."""
        html = '''
        <video>
            <source src="video_low.mp4" data-quality="480p">
            <source src="video_high.mp4" data-quality="1080p">
            <source src="video_medium.mp4" data-quality="720p">
        </video>
        '''
        result = discover_media_url(html, prefer_highest_quality=True)
        # Should select 1080p (highest resolution)
        self.assertEqual(result, "video_high.mp4")
    
    def test_extract_quality_info(self):
        """Test quality info extraction."""
        html = '<source src="test.mp4" data-width="1920" data-height="1080" data-quality="1080p">'
        soup = BeautifulSoup(html, "html.parser")
        source = soup.select_one("source")
        
        width, height, label = _extract_quality_info(source)
        self.assertEqual(width, 1920)
        self.assertEqual(height, 1080)
        self.assertEqual(label, "1080p")
    
    def test_prefer_highest_quality_false(self):
        """Test that first source is returned when prefer_highest_quality is False."""
        html = '''
        <video>
            <source src="video_720p.mp4" data-height="720">
            <source src="video_1080p.mp4" data-height="1080">
        </video>
        '''
        result = discover_media_url(html, prefer_highest_quality=False)
        self.assertEqual(result, "video_720p.mp4")  # First source


if __name__ == "__main__":
    unittest.main()

