"""Writer pack: generated digest mirrors the Engine and detects staleness."""
import unittest
from unittest import mock

from hcb import util, writer_pack

REF = util.ROOT / ".hermes/skills/career-buddy/hcb-writer/references"


class WriterPack(unittest.TestCase):
    def test_digest_covers_every_evidence_unit_and_role(self):
        root = util.facts_root()
        text = writer_pack.build()
        for e in util.load_yaml(root / "facts/evidence.yaml")["evidence"]:
            self.assertIn(f"**{e['id']}**", text)
            self.assertIn(e["claim"].strip()[:60], text)
        for r in util.load_yaml(root / "facts/roles.yaml")["roles"]:
            self.assertIn(str(r["title_on_documents"]), text)
        for p in util.load_yaml(root / "facts/prohibitions.yaml")["patterns"]:
            self.assertIn(p["reason"], text)

    def test_referee_contacts_excluded(self):
        root = util.facts_root()
        refs = util.load_yaml(root / "facts/roles.yaml").get("referees") or []
        text = writer_pack.build()
        for ref in refs if isinstance(refs, list) else refs.values():
            for k in ("phone", "email"):
                if isinstance(ref, dict) and ref.get(k):
                    self.assertNotIn(str(ref[k]), text)

    def test_stale_detection(self):
        writer_pack.write()
        self.assertTrue(writer_pack.check()["fresh"])
        fake = {s: "0" * 64 for s in writer_pack.SOURCES}
        with mock.patch.object(writer_pack, "source_hashes", return_value=fake):
            self.assertFalse(writer_pack.check()["fresh"])

    def test_method_pack_present_and_scanner_safe(self):
        for name in ("method.md", "voice.md", "schemas.md", "contracts.md"):
            text = (REF / name).read_text()
            self.assertGreater(len(text), 1000, name)
            self.assertNotIn("—", text, f"em dash in {name}")

    def test_digest_not_tracked_by_git(self):
        self.assertIn("private/", (util.ROOT / ".gitignore").read_text())
        self.assertTrue(str(writer_pack._out()).startswith(str(util.private_dir())))


if __name__ == "__main__":
    unittest.main()
