"""The Engine renders exactly the plan's documents: a cover letter only when the ad asks for one
(the user, 2026-11-26: a Tasmanian State Service ad wanted CV + Short Form Application and forbade a letter)."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from hcb import engine, util
from tests.test_cv_engine_v2 import content

BUILD = util.ROOT / "engine" / "build"
LETTER = {"date": "1 January 2026", "recipient": ["Hiring Team"], "salutation": "Dear Hiring Team,",
          "paragraphs": [{"text": "I am applying for the role."}], "signoff": "Kind regards,"}
STATEMENT = {"title": ["Short Form Application"], "criteria": [{"heading": "Why", "text": "Because."}]}
TSS_PLAN = {"documents": [{"type": "cv"}, {"type": "selection_criteria", "display_name": "Short Form Application"}],
            "forbidden_documents": ["cover_letter"]}
STANDARD_PLAN = {"documents": [{"type": "cv"}, {"type": "cover_letter"}]}


class DocumentPlanCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def check(self, plan, c):
        if plan is not None:
            (self.folder / "document-plan.json").write_text(json.dumps(plan))
        (self.folder / "content.json").write_text(json.dumps(c))
        return engine.document_plan_check(self.folder)

    def test_cv_and_short_form_without_letter_passes(self):
        self.assertEqual(self.check(TSS_PLAN, content(statement=STATEMENT))["exit"], 0)

    def test_letter_when_the_ad_forbids_it_fails(self):
        r = self.check(TSS_PLAN, content(statement=STATEMENT, letter=LETTER))
        self.assertEqual(r["exit"], 1)
        self.assertIn("forbids", r["stdout_tail"])

    def test_planned_letter_missing_fails(self):
        self.assertEqual(self.check(STANDARD_PLAN, content())["exit"], 1)

    def test_planned_statement_missing_fails(self):
        self.assertEqual(self.check(TSS_PLAN, content())["exit"], 1)

    def test_standard_cv_and_letter_passes(self):
        self.assertEqual(self.check(STANDARD_PLAN, content(letter=LETTER))["exit"], 0)

    def test_no_plan_is_skipped(self):
        self.assertEqual(self.check(None, content(letter=LETTER))["exit"], 0)


@unittest.skipUnless(shutil.which("node") and (BUILD / "node_modules" / "js-yaml").exists(),
                     "node and engine/build/node_modules needed to render")
class RenderOnlyPlannedDocuments(unittest.TestCase):
    def test_no_letter_rendered_and_stale_letter_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "cover-letter.md").write_text("stale")
            (folder / "cover-letter.html").write_text("stale")
            cpath = folder / "content.json"
            cpath.write_text(json.dumps(content(statement=STATEMENT)))
            for script in ("make-md.js", "make-html.js"):
                r = subprocess.run(["node", str(BUILD / script), str(cpath)], capture_output=True, text=True,
                                   cwd=BUILD.parent)
                self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse((folder / "cover-letter.md").exists())
            self.assertFalse((folder / "cover-letter.html").exists())
            self.assertTrue((folder / "selection-criteria.html").exists())


if __name__ == "__main__":
    unittest.main()
