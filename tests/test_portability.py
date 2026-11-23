"""Migration readiness check (`bin/hcb doctor --deploy`): every item has a VPS fix; secrets are never read."""
import unittest
from pathlib import Path
from unittest import mock

from hcb import portability


class Portability(unittest.TestCase):
    def test_every_check_says_how_to_fix_it_on_the_vps(self):
        s = portability.summary()
        self.assertEqual(s["total"], len(s["checks"]))
        for c in s["checks"]:
            self.assertTrue(c["item"] and c["on_vps"], c)
        self.assertEqual(s["ready"], not s["missing"])

    def test_secret_content_is_never_read(self):
        with mock.patch.object(Path, "read_text", side_effect=AssertionError("read")), \
             mock.patch.object(Path, "read_bytes", side_effect=AssertionError("read")):
            ok, detail = portability._secret(Path(__file__))
        self.assertIn("mode", detail)

    def test_missing_secret(self):
        self.assertEqual(portability._secret(Path("/nonexistent/x")), (False, "missing"))


if __name__ == "__main__":
    unittest.main()
