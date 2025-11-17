import unittest
from downloader.discover import discover_media_url
from urllib.parse import urljoin


class TestIntegrationProbe(unittest.TestCase):
    def test_discover_media_url(self):
        html = '<html><body><video><source src="//media.cdn.motherless.com/vid.mp4"></video></body></html>'
        media = discover_media_url(html)
        self.assertIn('motherless.com', media)

    def test_urljoin(self):
        base = 'https://motherless.com/94ACE56'
        rel = '//media.cdn.motherless.com/vid.mp4'
        abs_url = urljoin(base, rel)
        self.assertTrue(abs_url.startswith('https://'))
        self.assertIn('motherless.com', abs_url)


if __name__ == '__main__':
    unittest.main()
