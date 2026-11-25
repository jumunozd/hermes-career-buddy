"""Facts marked always_include (the user's AI skills, 2026-11-25) must be in every CV, or the pipeline fails."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from hcb import engine

EVIDENCE = """evidence:
  - id: ai_project
    role: null
    claim: "Directed a small AI automation project"
    status: verified
    always_include: true
  - id: other
    role: acme
    claim: "Something else"
    status: verified
"""
CREDS = """credentials:
  - id: ai-course
    name: "AI Fluency: Framework and Foundations"
    always_include: true
  - id: excel
    name: "Excel"
"""


class AlwaysInclude(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "facts").mkdir()
        (root / "facts" / "evidence.yaml").write_text(EVIDENCE)
        (root / "facts" / "credentials.yaml").write_text(CREDS)
        self.folder = root / "v1"; self.folder.mkdir()
        self.p = mock.patch("hcb.engine.facts_root", return_value=root); self.p.start()

    def tearDown(self):
        self.p.stop(); self.tmp.cleanup()

    def _content(self, **c):
        (self.folder / "content.json").write_text(json.dumps(c))
        return engine.always_include_check(self.folder)

    def test_passes_when_cited_and_listed(self):
        r = self._content(projects=[{"name": "AI", "evidence": ["ai_project"]}],
                          certifications=["AI Fluency: Framework and Foundations | Anthropic | 2026"])
        self.assertEqual(r["exit"], 0, r)

    def test_fails_when_the_ai_facts_are_missing(self):
        r = self._content(experience=[{"bullets": [{"text": "x", "evidence": ["other"]}]}], certifications=["Excel"])
        self.assertEqual(r["exit"], 1)
        self.assertIn("ai_project", r["stdout_tail"]); self.assertIn("ai-course", r["stdout_tail"])


if __name__ == "__main__":
    unittest.main()
