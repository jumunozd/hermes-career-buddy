"""P-5 leak guard: the publishable tree is clean, and planted personal data is caught."""
import tempfile
import unittest
from pathlib import Path

from hcb import privacy, util


class PrivacyScan(unittest.TestCase):
    def test_publishable_tree_is_clean(self):
        hits = privacy.scan()
        self.assertEqual(hits, [], f"{len(hits)} leak(s): run bin/hcb privacy-scan --verbose")

    def test_planted_values_are_caught_and_masked(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "notes.md"
            f.write_text("Call me on 0412 987 654 or write to someone.real@gmail.com\n"
                         "id 6123456789 and key a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6\n", encoding="utf-8")
            kinds = {h["kind"] for h in privacy.scan([f])}
            self.assertTrue({"phone", "email", "long_id", "token_like"} <= kinds, kinds)
            self.assertFalse(any("987 654" in h["value"] or "real@" in h["value"] for h in privacy.scan([f])))

    def test_placeholders_and_role_inboxes_pass(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "ok.md"
            f.write_text("Alex Example, 0400 000 000, alex@example.com, careers@employer.com.au\n", encoding="utf-8")
            self.assertEqual([h for h in privacy.scan([f]) if h["kind"] != "private_fact"], [])

    @unittest.skipUnless((util.ROOT / "private" / "facts" / "identity.yaml").exists(), "needs the private zone")
    def test_private_facts_are_caught(self):
        terms, names = privacy.private_terms(util.ROOT / "private")
        self.assertTrue(terms and names)
        some = sorted(terms - privacy.PLACES)[0]
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "leak.md"
            f.write_text(f"worked at {some}\n", encoding="utf-8")
            self.assertTrue(any(h["kind"] == "private_fact" for h in privacy.scan([f], util.ROOT / "private")))

    @unittest.skipUnless((util.ROOT / "private" / "facts" / "identity.yaml").exists(), "needs the private zone")
    def test_contact_names_and_mailbox_addresses_are_private(self):
        terms, _ = privacy.private_terms(util.ROOT / "private")
        import json
        for f in (util.ROOT / "private" / "state" / "research").glob("*/contacts.json"):
            data = json.loads(f.read_text(encoding="utf-8"))
            for c in (data.get("contacts") if isinstance(data, dict) else data) or []:
                if isinstance(c, dict) and len(str(c.get("name") or "").split()) >= 2:
                    self.assertIn(c["name"], terms)
        box = util.ROOT / "private" / "config" / "alerts-mailbox.yaml"
        if box.exists():
            self.assertTrue(any("@" in t for t in terms))

    def test_private_zone_is_ignored_by_git(self):
        self.assertIn("private/", (util.ROOT / ".gitignore").read_text())
        self.assertFalse(any("private/" in str(p.relative_to(util.ROOT)) for p in privacy.publishable_files()))


if __name__ == "__main__":
    unittest.main()
