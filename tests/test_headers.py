import unittest
from downloader.utils import perform_head_validation, validate_url


class TestHeaders(unittest.TestCase):
    def test_content_range_fallback(self):
        headers = {
            "Content-Type": "video/mp4",
            "Content-Range": "bytes 0-0/12345",
        }
        res = perform_head_validation(206, headers)
        self.assertTrue(res.is_valid)
        self.assertEqual(res.total_bytes, 12345)

    def test_allowed_host_variants(self):
        self.assertTrue(validate_url("https://motherless.com/ABC").is_valid)
        self.assertTrue(validate_url("https://media.cdn.motherless.com/x/y").is_valid)
        self.assertTrue(validate_url("https://motherlessmedia.com/video.mp4").is_valid)


if __name__ == "__main__":
    unittest.main()
