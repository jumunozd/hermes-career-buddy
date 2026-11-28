"""P-16 (2026-11-28): agents read the layout as data; form problems that only rendering shows are caught by code.
- layout_check reads fit.py's layout.json (fonts actually used, overlaps, overflow, empty pages).
- ats_check TRUNC: every bullet / paragraph is in the PDF and DOCX text, start and end.
- Golden render: the demo persona's CV page 1 is rendered and compared with an approved picture, so a template or
  font break is caught once, here, never in an application."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from hcb import engine, util
from tests.test_cv_engine_v2 import content

BUILD = util.ROOT / "engine" / "build"
GOLDEN = util.ROOT / "tests" / "golden" / "cv-demo-page1.png"
sys.path.insert(0, str(BUILD))


def _env():
    e = dict(os.environ)
    e["HCB_PRIVATE_DIR"] = str((util.ROOT / "examples" / "candidate").resolve())
    return e


class LayoutCheck(unittest.TestCase):
    def run_check(self, docs):
        with tempfile.TemporaryDirectory() as tmp:
            ok = not any(v["issues"] for v in docs.values())
            (Path(tmp) / "layout.json").write_text(json.dumps({"documents": docs, "ok": ok}))
            return engine.layout_check(Path(tmp))

    def test_clean_layout_passes_and_is_summarised(self):
        r = self.run_check({"cv": {"pages": [{"page": 1, "used_pct": 97, "last": "Followed strict WHS"}],
                                   "fonts": ["Helvetica Neue"], "issues": [], "warnings": []}})
        self.assertEqual(r["exit"], 0)
        self.assertIn("p1 97%", r["stdout_tail"])

    def test_render_problem_fails(self):
        r = self.run_check({"cv": {"pages": [], "fonts": ["GENERIC"], "warnings": [],
                                   "issues": ["pagina 1: texto encimado 'a' / 'b'"]}})
        self.assertEqual(r["exit"], 1)
        self.assertIn("FAIL LAYOUT", r["stdout_tail"])

    def test_missing_layout_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(engine.layout_check(Path(tmp))["exit"], 1)


class Truncation(unittest.TestCase):
    def test_cut_bullet_is_found(self):
        import ats_check
        C = {"experience": [{"bullets": [{"text": "Reduced the recurring monthly server cost on the same process "
                                                  "from approximately A$300 to approximately A$75 per month."}]}]}
        full = "Reduced the recurring monthly server cost on the same process from approximately A$300 to approximately A$75 per month."
        self.assertEqual(ats_check.check_complete(full, "cv", C), [])
        cut = "Reduced the recurring monthly server cost on the same process from approx"
        self.assertEqual([c for c, _ in ats_check.check_complete(cut, "cv", C)], ["TRUNC"])


def _chrome():
    """Same lookup as fit.py, without importing it (fit reads the facts of whatever persona is active)."""
    for c in (os.environ.get("HCB_CHROME"), "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              shutil.which("chromium"), shutil.which("chromium-browser"), shutil.which("google-chrome")):
        if c and Path(c).exists():
            return c
    return None


def render_page1(out_png: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cpath = Path(tmp) / "content.json"
        shutil.copy(util.ROOT / "tests" / "golden" / "cv-demo-content.json", cpath)   # fixed demo persona content
        subprocess.run(["node", str(BUILD / "make-html.js"), str(cpath)], check=True, capture_output=True,
                       cwd=BUILD.parent, env=_env())
        html = next(Path(tmp).glob("cv-*.html"))
        subprocess.run([_chrome(), "--headless", "--disable-gpu", "--hide-scrollbars", "--window-size=794,1123",
                        "--virtual-time-budget=3000", f"--screenshot={out_png}", f"file://{html}"],
                       check=True, capture_output=True)


@unittest.skipUnless(sys.platform == "darwin" and shutil.which("node") and (BUILD / "node_modules" / "js-yaml").exists()
                     and _chrome() and GOLDEN.exists(), "golden render needs macOS, Chrome, node and the reference")
class GoldenRender(unittest.TestCase):
    MAX_DIFF = 0.02          # share of pixels allowed to differ (anti-aliasing noise)

    def test_cv_page1_matches_the_approved_picture(self):
        from PIL import Image, ImageChops
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "now.png"
            render_page1(out)
            a = Image.open(GOLDEN).convert("L")
            b = Image.open(out).convert("L").resize(a.size)
            diff = ImageChops.difference(a, b).point(lambda v: 255 if v > 40 else 0)
            share = sum(1 for v in diff.getdata() if v) / (a.size[0] * a.size[1])
            self.assertLess(share, self.MAX_DIFF, f"CV render differs from tests/golden ({share:.1%}): "
                                                  "a template or font change? Approve a new picture only on purpose.")


if __name__ == "__main__":
    if "--update-golden" in sys.argv:
        render_page1(GOLDEN)
        print("updated", GOLDEN)
    else:
        unittest.main()
