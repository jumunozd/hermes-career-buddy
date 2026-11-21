"""Daily backup: retention keeps the newest 7 plus one per week for 4 weeks."""
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from hcb import backup


class Retention(unittest.TestCase):
    def test_prune(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            start = datetime(2026, 11, 19, 3, 0)
            for i in range(40):
                (d / f"hcb-backup-{(start - timedelta(days=i)):%Y%m%d-%H%M}.tar.enc").write_bytes(b"x")
            removed = backup.prune(d)
            left = sorted(p.name for p in d.glob("*.enc"))
        self.assertEqual(len(left), 40 - len(removed))
        self.assertIn("hcb-backup-20261119-0300.tar.enc", left)
        self.assertLessEqual(len(left), 7 + 4)
        self.assertGreaterEqual(len(left), 7)


if __name__ == "__main__":
    unittest.main()
