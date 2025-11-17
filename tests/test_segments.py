import unittest
from downloader.segments import compute_segments, adjust_segments_for_resume


class TestSegments(unittest.TestCase):
    def test_single(self):
        self.assertEqual(compute_segments(100, 1), [(0, 99)])

    def test_even(self):
        self.assertEqual(compute_segments(100, 4), [(0,24),(25,49),(50,74),(75,99)])

    def test_remainder(self):
        segs = compute_segments(10, 3)
        self.assertEqual(sum(e - s + 1 for s, e in segs), 10)
        self.assertEqual(segs[0][0], 0)
        self.assertEqual(segs[-1][1], 9)

    def test_adjust_resume(self):
        segs = [(0, 24), (25, 49), (50, 74), (75, 99)]
        adj = adjust_segments_for_resume(segs, 30)
        self.assertEqual(adj[0], (30, 49))
        self.assertEqual(adj[-1], (75, 99))
        adj2 = adjust_segments_for_resume(segs, 120)
        self.assertEqual(adj2, [])


if __name__ == '__main__':
    unittest.main()
