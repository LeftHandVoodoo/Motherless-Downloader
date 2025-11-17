import unittest
from downloader.utils import (
    validate_url,
    perform_head_validation,
    extract_filename_from_content_disposition,
    UrlValidationResult,
    HeadValidationResult,
)


class TestValidation(unittest.TestCase):
    def test_validate_url_https_and_domain(self):
        ok = validate_url("https://media.cdn.motherless.com/path/file.mp4")
        self.assertTrue(ok.is_valid)

        # Accept base domain
        ok2 = validate_url("https://motherless.com/94ACE56")
        self.assertTrue(ok2.is_valid)

        bad_scheme = validate_url("http://motherless.com/file")
        self.assertFalse(bad_scheme.is_valid)
        self.assertIn("https", bad_scheme.message.lower())

        bad_host = validate_url("https://example.com/file")
        self.assertFalse(bad_host.is_valid)
        self.assertIn("motherless", bad_host.message.lower())

    def test_extract_filename_from_header(self):
        h1 = 'attachment; filename="video.mp4"'
        self.assertEqual(extract_filename_from_content_disposition(h1), "video.mp4")
        h2 = "attachment; filename*=UTF-8''clip%20name.mp4"
        self.assertEqual(extract_filename_from_content_disposition(h2), "clip%20name.mp4")
        self.assertIsNone(extract_filename_from_content_disposition(None))

    def test_head_validation_success(self):
        headers = {
            "Content-Length": "1024",
            "Content-Type": "video/mp4",
            "Accept-Ranges": "bytes",
            "Content-Disposition": 'attachment; filename="clip.mp4"',
        }
        res = perform_head_validation(200, headers)
        self.assertTrue(res.is_valid)
        self.assertEqual(res.total_bytes, 1024)
        self.assertTrue(res.accept_ranges_bytes)
        self.assertEqual(res.suggested_filename, "clip.mp4")

    def test_head_validation_errors(self):
        self.assertFalse(perform_head_validation(404, {}).is_valid)
        self.assertFalse(perform_head_validation(200, {"Content-Type": "video/mp4"}).is_valid)
        self.assertFalse(perform_head_validation(200, {"Content-Length": "abc", "Content-Type": "video/mp4"}).is_valid)
        self.assertFalse(perform_head_validation(200, {"Content-Length": "10", "Content-Type": "text/plain"}).is_valid)


if __name__ == "__main__":
    unittest.main()
