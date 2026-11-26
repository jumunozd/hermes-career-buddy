"""Selected Projects (the user, 2026-11-26): heading "Selected Projects", page 2 (after experience) by default,
and business achievements stay in professional experience (fit.py rejects employer evidence in projects)."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.test_cv_engine_v2 import EV, ROLES, content, fit, util

BUILD = util.ROOT / "engine" / "build"
EMPLOYERS = {r["id"] for r in ROLES if r.get("title_on_documents")}
EMPLOYER_EV = next(e["id"] for e in EV if e.get("status") == "verified" and e.get("role") in EMPLOYERS)
FREE_EV = next((e["id"] for e in EV if e.get("status") == "verified" and e.get("role") not in EMPLOYERS), None)


def errors(c):
    with tempfile.TemporaryDirectory() as tmp:
        return fit.check_v2(c, Path(tmp))[0]


def _env():
    """Node runs from engine/: make a relative HCB_PRIVATE_DIR (CI demo persona) absolute."""
    e = dict(os.environ)
    if e.get("HCB_PRIVATE_DIR"):
        e["HCB_PRIVATE_DIR"] = str(Path(e["HCB_PRIVATE_DIR"]).resolve())
    return e


class ProjectsKeepBusinessInExperience(unittest.TestCase):
    def test_employer_achievement_in_projects_fails(self):
        c = content(projects=[{"name": "X", "line": "Something.", "evidence": [EMPLOYER_EV]}])
        self.assertTrue(any("experiencia profesional" in e for e in errors(c)))

    @unittest.skipUnless(FREE_EV, "no evidence without an employer in this persona")
    def test_project_without_employer_has_no_such_error(self):
        c = content(projects=[{"name": "X", "line": "Something.", "evidence": [FREE_EV]}])
        self.assertFalse(any("experiencia profesional" in e for e in errors(c)))


@unittest.skipUnless(shutil.which("node") and (BUILD / "node_modules" / "js-yaml").exists(),
                     "node and engine/build/node_modules needed to render")
class SelectedProjectsDefaults(unittest.TestCase):
    def test_heading_and_after_experience_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            cpath = Path(tmp) / "content.json"
            c = content(projects=[{"name": "Demo project", "line": "Did a thing.", "evidence": []}])
            cpath.write_text(json.dumps(c))
            r = subprocess.run(["node", str(BUILD / "make-md.js"), str(cpath)], capture_output=True, text=True,
                               cwd=BUILD.parent, env=_env())
            self.assertEqual(r.returncode, 0, r.stderr)
            md = next(Path(tmp).glob("cv-*.md")).read_text()
            self.assertIn("## SELECTED PROJECTS", md)
            self.assertLess(md.index("EXPERIENCE"), md.index("## SELECTED PROJECTS"))


if __name__ == "__main__":
    unittest.main()
