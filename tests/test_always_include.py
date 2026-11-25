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


class TitleStyle(unittest.TestCase):
    """Style v3 (the user, 2026-11-25): header by the ad's engineering requirement, background in the Summary."""
    IDENT = 'professional_identity: "Industrial Engineer"\ncontact_line_2_display: "FULL RIGHT TO WORK | Driver Licence (Class C)"\n'

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "facts").mkdir()
        (root / "facts" / "identity.yaml").write_text(self.IDENT)
        self.folder = root / "v1"; self.folder.mkdir()
        cfg = {"cv": {"title_rule": "by_engineering_requirement", "background_in_first_sentence": True,
                      "contact_line_2_from_facts": True}}
        self.ps = [mock.patch("hcb.engine.facts_root", return_value=root),
                   mock.patch("hcb.util.config", return_value=cfg)]
        for p in self.ps:
            p.start()

    def tearDown(self):
        for p in self.ps:
            p.stop()
        self.tmp.cleanup()

    def _run(self, req, line, summary, contact="FULL RIGHT TO WORK | Driver Licence (Class C)"):
        (self.folder / "targets.yaml").write_text("" if req is None else f"engineering_required: {str(req).lower()}\n")
        (self.folder / "content.json").write_text(json.dumps(
            {"identity_line": line, "professional_summary": summary, "contact_line_2": contact}))
        return engine.style_check(self.folder)

    def test_engineering_role_needs_the_credential_title(self):
        self.assertEqual(self._run(True, "Industrial Engineer", "Engineer with ...")["exit"], 0)
        self.assertEqual(self._run(True, "Project Administration", "x.")["exit"], 1)

    def test_non_engineering_role_uses_role_title_and_background_first(self):
        ok = self._run(False, "Project Documentation and Administration",
                       "Project documentation professional with an Industrial Engineering background. More.")
        self.assertEqual(ok["exit"], 0, ok)
        late = self._run(False, "Project Documentation and Administration",
                         "Project documentation professional. An Industrial Engineer later.")
        self.assertEqual(late["exit"], 1)
        self.assertEqual(self._run(False, "Industrial Engineer", "Industrial Engineer with x.")["exit"], 1)

    def test_missing_decision_and_contact_line(self):
        self.assertIn("engineering_required", self._run(None, "X", "Y.")["stdout_tail"])
        self.assertIn("contact_line_2", self._run(True, "Industrial Engineer", "x.", contact="other")["stdout_tail"])


class ReductionsAsPercentage(TitleStyle):
    def _letter(self, text):
        (self.folder / "targets.yaml").write_text("engineering_required: true\n")
        (self.folder / "content.json").write_text(json.dumps(
            {"identity_line": "Industrial Engineer", "professional_summary": "x.",
             "contact_line_2": "FULL RIGHT TO WORK | Driver Licence (Class C)", "letter": {"paragraphs": [{"text": text}]}}))
        cfg = {"cv": {"title_rule": "by_engineering_requirement", "reductions_as_percentage": True,
                      "contact_line_2_from_facts": True}}
        with mock.patch("hcb.util.config", return_value=cfg):
            return engine.style_check(self.folder)

    def test_reduction_needs_its_percentage(self):
        bad = self._letter("I cut monthly server costs from A$300 to A$75.")
        self.assertEqual(bad["exit"], 1); self.assertIn("75%", bad["stdout_tail"])
        self.assertEqual(self._letter("I cut monthly server costs by 75% (from A$300 to A$75).")["exit"], 0)
        self.assertEqual(self._letter("Output went from 4,500 to 5,000 kg.")["exit"], 0)   # increases are not reductions
