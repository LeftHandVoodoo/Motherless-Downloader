import unittest
from pathlib import Path
import json
import tempfile

from downloader.state import (
    build_part_path,
    build_sidecar_path,
    save_sidecar_atomic,
    load_sidecar,
    compute_resume_offset,
    make_sidecar_for_url,
    sidecar_matches_url,
    SidecarState,
)


class TestStateHelpers(unittest.TestCase):
    def test_paths_and_sidecar_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            final = Path(td) / "file.mp4"
            part = build_part_path(final)
            side = build_sidecar_path(final)

            self.assertTrue(str(part).endswith(".part"))
            self.assertTrue(str(side).endswith(".part.json"))

            # create part with some bytes
            part.write_bytes(b"x" * 10)
            self.assertEqual(compute_resume_offset(final), 10)

            st = make_sidecar_for_url(final, "https://cdn.motherless.com/a", 100, 10)
            save_sidecar_atomic(side, st)
            loaded = load_sidecar(side)
            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(loaded.total_size, 100)
            self.assertEqual(loaded.received_bytes, 10)
            self.assertTrue(sidecar_matches_url(loaded, "https://cdn.motherless.com/a"))
            self.assertFalse(sidecar_matches_url(loaded, "https://cdn.motherless.com/b"))


if __name__ == "__main__":
    unittest.main()
